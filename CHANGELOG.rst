0.8.0
-----

* __setters__ are no longer supported.
* __form_new_options__ and __form_edit_options__ are now available to set options specific to new or edit forms.
* get_all now logs exception when unable to retrieve data
* post, put and delete now return the created/edited/deleted object when called from child class method
* When subclassed error handler are now properly retrieved from the subclass when overridden.
* post, put and delete now redirect after the controller has been executed, not during.

0.7.4
-----
* Allow custom provider selector

0.5.6
-----------------------
* Make possible to choose whenever to rollback session or abort transaction when a database error occurs using the tgext.crud.abort_transactions option

0.4 (Jan. 31, 2012)
-----------------------
 * Support filtering results in table view when passing arguments to the url
 * Added keep_params option which makes possible to keep around
filters, useful when you want to administer only a subset of the
available objects.

0.3 (Sept. 30, 2009)
----------------------

* Mako template support
* Title template fixes
* Provider session bug fixed 
* TW 0.9.7.2 support
* Pagination added.

0.2.x
------
Prehistory (should have kept better logs)
