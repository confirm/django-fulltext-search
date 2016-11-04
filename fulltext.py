# -*- coding: utf-8 -*-
from django.db import models, connection


class SearchQuerySet(models.query.QuerySet):
    '''
    QuerySet which supports MySQL and MariaDB full-text search.
    '''

    def __init__(self, fields=None, **kwargs):
        super(SearchQuerySet, self).__init__(**kwargs)
        self.search_fields = fields

    def get_query_set(self, query, columns, mode):
        '''
        Returns the query set for the columns and search mode.
        '''
        # Create the WHERE MATCH() ... AGAINST() expression.
        fulltext_columns = ', '.join(columns)
        where_expression = ('MATCH({}) AGAINST("%s" {})'.format(fulltext_columns, mode))

        # Get query set via extra() method.
        return self.extra(where=[where_expression], params=[query])

    def search(self, query, fields=None, mode=None):
        '''
        Runs a fulltext search against the fields defined in the method's
        kwargs. If no fields are defined in the method call, then the fields
        defined in the constructor's kwargs will be used.

        Just define a query (the search term) and a fulltext search will be
        executed. In case mode is set to None, the method will automatically
        switch to "BOOLEAN" in case any boolean operators were found.
        Of course you can set the search mode to any type you want, e.g.
        "NATURAL LANGUAGE".
        '''

        #
        # Get all requried attributes and initialize our empty sets.
        #

        meta       = self.model._meta
        quote_name = connection.ops.quote_name
        seperator  = models.constants.LOOKUP_SEP

        columns        = set()
        related_fields = set()

        #
        # Loop through the defined search fields to build a list of all
        # searchable columns. We need to differ between simple fields and
        # fields with a related model, because the meta data of those fields
        # are stored in the related model itself.
        #

        fields = self.search_fields if fields == None else fields

        for field in fields:

            # Handling fields with a related model.
            if seperator in field:
                field, rfield = field.split(seperator)
                rmodel        = meta.get_field(field, many_to_many=False).related_model
                rmeta         = rmodel._meta
                table         = rmeta.db_table
                column        = rmeta.get_field(rfield, many_to_many=False).column
                related_fields.add(field)

            # Handle fields without a related model.
            else:
                table  = meta.db_table
                column = meta.get_field(field, many_to_many=False).column

            # Add field with `table`.`column` style to columns set.
            columns.add('{}.{}'.format(quote_name(table), quote_name(column)))

        #
        # We now have all the required informations to build the query with the
        # fulltext "MATCH(…) AGAINST(…)" WHERE statement. However, we also need
        # to conside the search mode. Thus, if the mode argument is set to
        # None, we need to inspect the search query and enable the BOOLEAN mode
        # in case any boolean operators were found. This is also a workaround
        # for using at-signs (@) in search queries, because we don't enable the
        # boolean mode in case no other operator was found.
        #

        # Set boolean mode if mode argument is set to None.
        if mode is None and any(x in query for x in '+-><()*"'):
            mode = 'BOOLEAN'

        # Convert the mode into a valid "IN … MODE" or empty string.
        if mode is None:
            mode = ''
        else:
            mode = 'IN {} MODE'.format(mode)

        # Get the query set.
        query_set = self.get_query_set(query, columns, mode)

        #
        # If related fields were involved we've to select them as well.
        #

        if related_fields:
            query_set = query_set.select_related(','.join(related_fields))

        # Return query_set.
        return query_set

    def count(self):
        ''' Returns the count database records. '''
        #
        # We need to overwrite the default count() method. Unfortunately
        # Django's internal count() method will clone the query object and then
        # re-create the SQL query based on the default table and WHERE clause,
        # but without the related tables. So if related tables are included in
        # the query (i.e. JOINs), then Django will forget about the JOINs and
        # the MATCH() of the related fields will fail with an "unknown column"
        # error.
        #

        return self.__len__()


class SearchManager(models.Manager):
    '''
    SearchManager which supports MySQL and MariaDB full-text search.
    '''

    query_set = SearchQuerySet

    def __init__(self, fields=None):
        super(SearchManager, self).__init__()
        self.search_fields = fields

    def get_query_set(self):
        '''
        Returns the query_set.
        '''
        return self.query_set(model=self.model, fields=self.search_fields)

    def search(self, query, **kwargs):
        '''
        Runs a fulltext search against the fields defined in the method's kwargs
        or in the constructor's kwargs.

        For more informations read the documentation string of the
        SearchQuerySet's search() method.
        '''
        return self.get_query_set().search(query, **kwargs)