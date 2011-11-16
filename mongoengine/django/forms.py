# -*- coding: utf-8 -*-

"""
Helper functions for creating Form classes from mongoengine documents and database field objects.
"""

from django import forms
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.core.validators import RegexValidator
import mongoengine
from django.utils.datastructures import SortedDict

__all__ = (
        'DocForm', 'BaseDocForm', 'doc_to_dict', 'fields_for_doc', 'construct_instance'
        )

def construct_instance(form, instance, fields=None, exclude=None):
    """
    Constructs and returns a document instance form the bound ``form``'s
    ``cleaned_data``, but does not save the returned instance to the
    database.
    """
    cleaned_data = form.cleaned_data
    file_field_list = []

    for name, field in instance._fields.items():
        if not name in cleaned_data:
            continue
        if fields is not None and name not in fields:
            continue
        if exclude and name in exclude:
            continue

        if isinstance(field, (mongoengine.URLField, mongoengine.EmailField)):
            if cleaned_data[name]:
                field.__set__(instance, cleaned_data[name])
            else:
                field.__set__(instance, None)
            continue
        field.__set__(instance, cleaned_data[name])

    return instance


# DocForms #################################################

def doc_to_dict(instance, fields=None, exclude=None):
    """
    Returns a dict containing the data in ``instance`` suitable for passing as
    a Form's ``initial`` keyword argument.
    ``fields`` is an optional list of field names. If provided, only the named
    fields will be included in the returned dict.
    "exclude" is an optional list of field names. If provided, the named fields will be excluded form the returned dict, even if they are listed in the "fields" argument.
    """
    data = {}
    for name, field in instance._fields.items():
        if fields and not name in fields:
            continue
        if exclude and name in exclude:
            continue
        data[name] = field.__get__(instance, None)
    return data

def mongofield_to_formfield(mongo_field, widget=None, **kwargs):
    """
    Returns a corresponding form field to your document field with some argument value. If mongo_field is not a supported field types, None will be returned.
    """
    if mongo_field.choices:
        return forms.ChoiceField(choices = mongo_field.choices, widget = widget, label = mongo_field.verbose_name, required = mongo_field.required, help_text = mongo_field.help_text)
    if mongo_field.validation and callable(mongo_field.validation):
        validators = [mongo_field.validation]
    else:
        validators = []
    if mongo_field.__class__.__name__ == 'StringField':
        if mongo_field.regex:
            validators.append(RegexValidator(regex = mongo_field.regex))
        return forms.CharField(
                label = mongo_field.verbose_name,
                max_length = mongo_field.max_length,
                min_length = mongo_field.min_length,
                validators = validators,
                widget = widget,
                required = mongo_field.required,
                help_text = mongo_field.help_text
                )
    elif mongo_field.__class__.__name__ == 'IntField':
        return forms.IntegerField(
                min_value = mongo_field.min_value,
                max_value= mongo_field.max_value,
                validators = validators,
                widget = widget,
                label = mongo_field.verbose_name,
                required = mongo_field.required,
                help_text = mongo_field.help_text
                )
    elif mongo_field.__class__.__name__ == 'FloatField':
        return forms.FloatField(
                max_value = mongo_field.max_value,
                min_value = mongo_field.min_value,
                validators = validators,
                widget = widget,
                label = mongo_field.verbose_name,
                required = mongo_field.required,
                help_text = mongo_field.help_text
                )
    elif mongo_field.__class__.__name__ == 'BooleanField':
        return forms.BooleanField(
                widget = widget,
                label = mongo_field.verbose_name,
                required = mongo_field.required,
                help_text = mongo_field.help_text
                )
    elif mongo_field.__class__.__name__ == 'DateTimeField':
        return forms.DateTimeField(
                validators = validators,
                widget = widget,
                label = mongo_field.verbose_name,
                required = mongo_field.required,
                help_text = mongo_field.help_text
                )
    elif mongo_field.__class__.__name__ == 'DecimalField':
        return forms.DecimalField(
                max_value = mongo_field.max_value,
                min_value = mongo_field.min_value,
                validators = validators,
                widget = widget,
                label = mongo_field.verbose_name,
                required = mongo_field.required,
                help_text = mongo_field.help_text
                )
    elif mongo_field.__class__.__name__ == 'URLField':
        return forms.URLField(
                verify_exists = mongo_field.verify_exists,
                validators = validators,
                widget = widget,
                label = mongo_field.verbose_name,
                required = mongo_field.required,
                help_text = mongo_field.help_text
                )
    elif mongo_field.__class__.__name__ == 'FileField':
        return forms.FileField(
                validators = validators,
                widget = widget,
                label = mongo_field.verbose_name,
                required = mongo_field.required,
                help_text = mongo_field.help_text
                )
    elif mongo_field.__class__.__name__ == 'EmailField':
        return forms.EmailField(
                validators = validators,
                widget = widget,
                label = mongo_field.verbose_name,
                required = mongo_field.required,
                help_text = mongo_field.help_text
                )
    elif mongo_field.__class__.__name__ == 'ImageField':
        return forms.ImageField(
                validators = validators,
                widget = widget,
                label = mongo_field.verbose_name,
                required = mongo_field.required,
                help_text = mongo_field.help_text
                )
    else:
        return None

def fields_for_doc(doc, fields=None, exclude=None, widgets=None, formfield_callback=None):
    """
    Returns a ``SortedDict`` containing form fields for the given document.
    ``fields`` is an optional list of field names. If provided, only the namedfields will be included in the returned fields.
    "exclude" is an optional list of field names. If provided, the named fields will be excluded form the returned dict, even if they are listed in the "fields" argument.
    """
    field_list = []
    ignored = []
    for name, field in doc._fields.items():
        if fields is not None and not name in fields:
            continue
        if exclude and name in exclude:
            continue
        if widgets and name in widgets:
            kwargs = {'widget': widgets[name]}
        else:
            kwargs = {}

        if formfield_callback is None:
            formfield = mongofield_to_formfield(field, **kwargs)
            if not formfield:
                raise TypeError(("%s is an unsupported field types at the moment, you should put it in the exclude list") % field)
        elif not callable(formfield_callback):
            raise TypeError('formfiled_callback must be a function or callable')
        else:
            formfield = formfield_callback(field, **kwargs)

        if formfield:
            field_list.append((name, formfield))
        else:
            ignored.append(name)
    field_dict = SortedDict(field_list)
    if fields:
        field_dict = SortedDict(
                [(f, field_dict.get(f)) for f in fields
                    if ((not exclude) or (exclude and f not in exclude) and (f not in ignored))]
                )
    return field_dict

class DocFormOptions(object):
    def __init__(self, options=None):
        self.document = getattr(options, 'document', None)
        self.fields = getattr(options, 'fields', None)
        self.exclude = getattr(options, 'exclude', None)
        self.widgets = getattr(options, 'widgets', None)

class DocFormMetaclass(type):
    def __new__(cls, name, bases, attrs):
        formfield_callback = attrs.pop('formfield_callback', None)
        try:
            parents = [b for b in bases if issubclass(b, DocForm)]
        except NameError:
            # We are defining DocForm itself
            parents = None
        declared_fields = forms.forms.get_declared_fields(bases, attrs, False)
        new_class = super(DocFormMetaclass, cls).__new__(cls, name, bases, attrs)
        if not parents:
            return new_class

        if 'media' not in attrs:
            new_class.media = forms.widgets.media_property(new_class)
        opts = new_class._meta = DocFormOptions(getattr(new_class, 'Meta', None))
        if opts.document:
            # If a document is defined, extract form fields from it.
            fields = fields_for_doc(opts.document, opts.fields, opts.exclude, opts.widgets, formfield_callback)
            # make sure opts.fields doesn't specify an invalid field
            none_doc_fields = [k for k, v in fields.iteritems() if not v]
            missing_fields = set(none_doc_fields) - set(declared_fields.keys())
            if missing_fields:
                message = 'Unknown field(s) (%s) specified for %s'
                message = message % (','.join(missing_fields), opts.document.__name__)
                raise FieldError(message)
            # Override default document fields with any custom declared ones
            #(plusm, include all the other declared fields).
            fields.update(declared_fields)
        else:
            fields = declared_fields
        new_class.declared_fields = declared_fields
        new_class.base_fields = fields
        return new_class

class BaseDocForm(forms.BaseForm):
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
            initial=None, error_class=forms.util.ErrorList, label_suffix=':',
            empty_permitted=False, instance=None):
        opts = self._meta
        if instance is None:
            if opts.document is None:
                raise ValueError('DocForm has no document class specified.')
            # if we didn't get an instance, instantiate a new one
            self.instance = opts.document()
            object_data = {}
        else:
            self.instance = instance
            object_data = doc_to_dict(instance, opts.fields, opts.exclude)
        # if initial was provided, it should override the values from instance
        if initial is not None:
            object_data.update(initial)
        super(BaseDocForm, self).__init__(data, files, auto_id, prefix, object_data,
                error_class, label_suffix, empty_permitted)

    def _update_errors(self, message_dict):
        for k, v in message_dict.items():
            if k != NON_FIELD_ERRORS:
                self._errors.setdefault(k, self.error_class()).append(v.message or "MongoEngine data valid failed in %s!" % k)
                # Remove the data from the cleaned_data dict since it was invalid
                if k in self.cleaned_data:
                    del self.cleaned_data[k]
        if NON_FIELD_ERRORS in message_dict:
            message = message_dict[NON_FIELD_ERRORS].message or "MongoEngine data valid failed"
            self._errors.setdefault(NON_FIELD_ERRORS, self.error_class()).append(message)

    def _post_clean(self):
        opts = self._meta
        #update the document instance with self.cleaned_data.
        self.instance = construct_instance(self, self.instance, opts.fields, opts.exclude)

        try:
            self.instance.validate()
        except mongoengine.ValidationError, e:
            self._update_errors(e.errors)

    def save(self, commit=False):
        """
        Saves this "form"'s cleaned_data into document instance "self.instance".
        If commit=True, then the changes to "instance" will be saved to the database. Returns "instance".
        """
        if isinstance(self.instance, mongoengine.EmbeddedDocument):
            if commit:
                raise ValueError("EmbeddedDocument doesn't support 'commit' paramiter.")
            return self.instance
        if isinstance(self.instance, mongoengine.Document):
            if self.instance.pk is None:
                fail_message = 'created'
            else:
                fail_message = 'changed'

        if self._errors:
            raise ValueError("The %s could not be %s because the data didn't validate." % (self.instance.__class__.__name__, fail_message))
        if commit:
            self.instance.save()
        return self.instance


class DocForm(BaseDocForm):
    """
    The use of this DocForm generic class is very similar with Django's ModelForm class in function. This is forms class for documents.
    If you're building a mongodb-driven app, chances are you'll have forms that map closely to documents. For example, you have a User Document class model, and you want to create a form that lets people submit new info message. To avoid define the field types repeatly, we develope this helper class.
    For example:
    Your User document model:
    class User(Document):
        first_name = StringField(verbose_name = _("First Name"), max_length=30, required = False)
        last_name = StringField(verbose_name = _("Last Name"), max_length=30, required = False)
        email = EmailField(required=False, verbose_name=_("Publiced Email"), help_text=_("This email address is not related to account emails, and will be public to others"))
        description = StringField(verbose_name = _("Brief Description"), max_length = 500, default = '', required = False, help_text = _("The length of this description should no more than 500 characters"))

    The corresponding ProjectNewForm
    class UserInfoEditForm(DocForm):
        class Meta:
            document = Project
            fields = ['first_name','email', 'description']
            exclude = ['last_name']
            widgets = {'description': forms.Textarea}

    >>form = UserInfoEditForm(user)

    1. To use this class, you should at least specify the document class you want to bound.
    2. Fields and exclude are optional list fields, if no fields and exclude list were specified then all the fields in the document class will be included.
    3. Widgets is a dict for specifying field widget.
    4. This class is inherited from BaseForm, we now supply save() method.
    5. We now only support the following field types:
    Document field            Form field
    StringField               CharField
    IntField                  IntegerField
    FloatField                FloatField
    BooleanField              BooleanField
    DateTimeField             DateTimeField
    DecimalField              DecimalField
    URLField                  URLField
    FileField                 FileField
    EmailField                EmailField
    ImageField                ImageField
    Fields that not in this list should be excluded from list and implement by yourself at this moment, including ComplexDateTimeField, ListField, SortedListField, DictField, MapField, ObjectIdField, ReferenceField, GenericReferenceField, EmbeddedDocumentField, BinaryField, GeoPointField, SequenceField.
    """
    __metaclass__ = DocFormMetaclass
