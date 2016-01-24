# -*- coding: utf-8 -*-
from django.db import models, connection


class SearchQuerySet(models.query.QuerySet):
    ''' QuerySet which supports MySQL and MariaDB full-text search. '''

    def __init__(self, fields=None, model=None, query=None, using=None, hints=None):
        super(SearchQuerySet, self).__init__(model=model, query=query, using=using, hints=hints)
        self._search_fields = fields

    def search(self, query):
        ''' Runs a fulltext search against the fields defined in the constructor. '''

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

        for field in self._search_fields:

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

        # Create the WHERE MATCH() ... AGAINST() expression.
        fulltext_columns = ', '.join(columns)
        where_expression = ('MATCH({}) AGAINST("%s" IN BOOLEAN MODE)'.format(fulltext_columns))

        # Get queryset via extra() method.
        queryset = self.extra(where=[match_expr], params=[query])

        #
        # If related fields were involved we've to select them as well.
        #

        if related_fields:
            queryset = queryset.select_related(','.join(related_fields))

        # Return queryset.
        return queryset

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
    ''' SearchManager which supports MySQL and MariaDB full-text search. '''

    def __init__(self, fields):
        super(SearchManager, self).__init__()
        self._search_fields = fields

    def get_query_set(self):
        ''' Returns the queryset. '''
        return SearchQuerySet(model=self.model, fields=self._search_fields)

    def search(self, query):
        ''' Runs a fulltext search against the fields defined in the constructor. '''
        return self.get_query_set().search(query)
