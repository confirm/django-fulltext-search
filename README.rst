===============================
Django Fulltext Search
===============================

.. image:: https://badge.fury.io/py/django-fulltext-search.png
    :target: http://badge.fury.io/py/django_fulltext_search

.. image:: https://travis-ci.org/confirm/django-fulltext-search.png?branch=master
        :target: https://travis-ci.org/confirm/django_fulltext_search

.. image:: https://pypip.in/d/django-fulltext-search/badge.png
        :target: https://pypi.python.org/pypi/django_fulltext_search


This repository provides a Python library for `Django <https://www.djangoproject.com>`_ which supports native full-text search capabilities for `MySQL <https://dev.mysql.com/doc/refman/5.6/en/fulltext-search.html>`_  and `MariaDB <https://mariadb.com/kb/en/mariadb/fulltext-index-overview/>`_ .

Django already `supports boolean full-text searches <https://docs.djangoproject.com/en/dev/ref/models/querysets/#search>`_ . However, with the integrated full-text search support you can only search one single column and IMHO there's currently no way to search over multiple columns.

Add fulltext index
------------------

Before you can run any full-text search you've to create at least one `full-text index <https://dev.mysql.com/doc/refman/5.6/en/create-index.html>`_ .
Unfortunately Djangos' `native migrations <https://docs.djangoproject.com/en/1.9/topics/migrations/>`_  doesn't support full-text indexes and the manual says:

> Note this is only available in MySQL and requires direct manipulation of the database to add the full-text index.

However, you can easily create your own migration by starting with an empty one::

    ./manage.py makemigrations --empty customer

Open the created migration file and add a `RunSQL command <https://docs.djangoproject.com/en/1.9/ref/migration-operations/#runsql>`_  to the `operations` list::

    operations = [
        migrations.RunSQL(
            ('CREATE FULLTEXT INDEX customer_fulltext_index ON customer_customer (first_name, last_name)',),
            ('DROP INDEX customer_fulltext_index on customer_customer',)
        )
    ]

Then migrate the database::

    ./manage.py migrate

Update your model
-----------------

If you want to add full-text search capabilities to your existing model you've to create a new `SearchManager()` instance and define it as your models' `objects` attribute::

    from django_fulltext_search import SearchManager

    class Customer(models.Model):
        ''' Customer model. '''

        # Enable full-text search support for first_name and last_name fields.
        objects    = SearchManager(['first_name', 'last_name'])
    
        first_name = models.CharField(max_length=32)
        last_name  = models.CharField(max_length=32)
        # more fields...

As you can see, you can create the `SearchManager()` with a **list of by default searchable fields**. This means you don't have to bother about the field names later when you search your model. However, if you don't want to specify default fields you can also create the ``SearchManager()`` object without any arguments::

    objects = SearchManager()

Search
------

The library currently supports `boolean full-text seaches <https://dev.mysql.com/doc/refman/5.6/en/fulltext-boolean.html>`_  by default if you use one of the operators (`+ - > < ( ) * "`) in your search query. Please note that the at-operator (`@`) will not enable the boolean search mode, which means you can also search for mail addresses, as long as you don't include any other operator in your search query.

To search your model use the new `search()` method of the models' queryset::

    Customer.objects.search('John*')

This only works if you've defined default fields in the constructor of the ``SearchManager()``. If you haven't set them or you want to search alternative fields you have to define a list of fields::

    Customer.objects.search('John*', ['first_name', 'last_name'])

The search method can also be called with keyword arguments:

* `query`: The search query itself
* `fields`: A list of fields
    * _optional_
    * _default are the fields defined in the ``SearchManager()``
* `mode`: Sets the search mode
    * _optional_
    * _default is `AUTO` which will enable `BOOLEAN` mode when a boolean operator is found in the ``fseaquery``
    * _can be set to a valid search mode, e.g. `BOOLEAN` or `NATURAL LANGUAGE`

**IMPORTANT:** Please remember you've to create a full-text index for the defined fields before you can search them.

Related models
--------------

If you want to search a related models' field (e.g. `models.ForeignKey`) you can also use the `__` syntax::

    SearchManager(['customer__first_name', 'customer__last_name']
