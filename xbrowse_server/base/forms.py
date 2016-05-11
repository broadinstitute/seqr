from django import forms
from django.forms.widgets import RadioSelect
from django.contrib.auth import authenticate
from django.utils.text import slugify
from django.contrib.auth.models import User

from xbrowse_server.base.models import Family, Individual, ANALYSIS_STATUS_CHOICES, COLLABORATOR_TYPES, ProjectPhenotype, FamilyGroup, Cohort
from xbrowse.parsers.fam_stuff import get_individuals_from_fam_file


class LoginForm(forms.Form):

    username_or_email = forms.CharField(max_length=100)
    password = forms.CharField(widget=forms.PasswordInput, max_length=100)

    def clean(self):
        """
        Try to get user from username or email
        Then check password is valid
        set self.user if everything okay, else raise ValidationError
        """
        if 'password' in self.cleaned_data and 'username_or_email' in self.cleaned_data:
            user = None
            if User.objects.filter(username=self.cleaned_data['username_or_email']).exists():
                user = User.objects.get(username=self.cleaned_data['username_or_email'])
            elif User.objects.filter(email=self.cleaned_data['username_or_email'].lower()).exists():
                user = User.objects.get(email=self.cleaned_data['username_or_email'].lower())
            if user is None:
                raise forms.ValidationError("This username/password combination is not valid")

            user = authenticate(username=user.username, password=self.cleaned_data['password'])
            if not user:
                raise forms.ValidationError("This username/password combination is not valid")

            self.user = user
        return self.cleaned_data


class SetUpAccountForm(forms.Form):

    name = forms.CharField(max_length=100, label="What is your name?")
    password1 = forms.CharField(widget=forms.PasswordInput, max_length=100, label="Set A Password")
    password2 = forms.CharField(widget=forms.PasswordInput, max_length=100, label="Confirm Password")

    def clean(self):
        """
        Make sure passwords match and password is >=8 lettters
        """
        if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data:
            if self.cleaned_data['password1'] != self.cleaned_data['password2']:
                raise forms.ValidationError("The two password fields didn't match.")
            if len(self.cleaned_data['password1']) < 8:
                raise forms.ValidationError("Password must be at least 8 characters")
        return self.cleaned_data


SEND_EMAIL_CHOICES = (('yes', 'Yes',), ('no', 'No',))


class AddUserForm(forms.Form):

    email = forms.EmailField(label="Email Address", max_length=80)
    name = forms.CharField(label="Name", max_length=80)
    username = forms.CharField(label="Username", max_length=30, required=False)
    send_email = forms.ChoiceField(widget=RadioSelect, choices=SEND_EMAIL_CHOICES)

    def clean_email(self):
        """
        Validate that the supplied email address is unique
        """
        if User.objects.filter(email__iexact=self.cleaned_data['email']):
            raise forms.ValidationError("This email address is already in use.")
        return self.cleaned_data['email']

    def clean(self):
        cleaned_data = super(AddUserForm, self).clean()
        if not cleaned_data.get('username'):
            cleaned_data['username'] = User.objects.make_random_password()
        if User.objects.filter(username=cleaned_data['username']).exists():
            raise forms.ValidationError("Username already in use")
        return cleaned_data


class AddFamilyForm(forms.Form):

    def __init__(self, project, *args, **kwargs):
        super(AddFamilyForm, self).__init__(*args, **kwargs)
        self.project = project

    family_id = forms.SlugField(max_length=40)
    short_description = forms.CharField(max_length=140)

    def clean_family_id(self):
        """
        Validate that family id is unique for this project
        """
        if Family.objects.filter(project=self.project, family_id=self.cleaned_data['family_id']).exists():
            raise forms.ValidationError("There is another family in this project with this family ID")
        return self.cleaned_data['family_id']


class EditFamilyForm(forms.Form):
    short_description = forms.CharField(max_length=500, required=False)
    about_family_content = forms.CharField(max_length=100000, widget=forms.Textarea, required=False)
    analysis_summary_content = forms.CharField(max_length=100000, widget=forms.Textarea, required=False)
    analysis_status = forms.ChoiceField(widget=forms.RadioSelect, choices=[(choice[0], choice[1][0]) for choice in ANALYSIS_STATUS_CHOICES])
    pedigree_image = forms.ImageField(label="Select an image", required=False)


class FAMFileForm(forms.Form):

    fam_file = forms.FileField()

    def clean(self):
        data = self.cleaned_data
        data['individuals'] = get_individuals_from_fam_file(self.cleaned_data['fam_file'])
        return data


class AddPhenotypeForm(forms.Form):

    name = forms.CharField(max_length=100)
    category = forms.CharField(max_length=30)
    datatype = forms.CharField(max_length=30)

    # takes a project
    def __init__(self, project, *args, **kwargs):
        super(AddPhenotypeForm, self).__init__(*args, **kwargs)
        self.project = project

    def clean(self):
        data = self.cleaned_data
        data['slug'] = slugify(self.cleaned_data['name'])
        if ProjectPhenotype.objects.filter(slug=data['slug'], project=self.project).exists():
            raise forms.ValidationError('A phenotype with this name already exists')
        return data


class AddCohortForm(forms.Form):

    name = forms.CharField(max_length=100)
    description = forms.CharField(max_length=100)
    indiv_ids = forms.CharField(max_length=100000)

    # takes a project
    def __init__(self, project, *args, **kwargs):
        super(AddCohortForm, self).__init__(*args, **kwargs)
        self.project = project

    def clean(self):
        data = self.cleaned_data
        data['cohort_id'] = slugify(self.cleaned_data['name'])
        if Cohort.objects.filter(project=self.project, cohort_id=data['cohort_id']).exists():
            raise forms.ValidationError("Name is already taken")
        indiv_id_list = self.cleaned_data['indiv_ids'].split('|')
        data['individuals'] = Individual.objects.filter(project=self.project, indiv_id__in=indiv_id_list)
        return data


class EditCohortForm(forms.Form):

    name = forms.CharField(max_length=100, label="Name of cohort")
    description = forms.CharField(max_length=100, label="Short description", required=False)

    def __init__(self, project, *args, **kwargs):
        super(EditCohortForm, self).__init__(*args, **kwargs)
        self.project = project

    def clean(self):
        data = self.cleaned_data
        data['cohort_id'] = slugify(self.cleaned_data['name'])
        if Cohort.objects.filter(project=self.project, cohort_id=data['cohort_id']).exists():
            raise forms.ValidationError("Name is already taken")
        return data


class AddFamilyGroupForm(forms.Form):

    name = forms.CharField(max_length=100)
    description = forms.CharField(max_length=100, required=False)
    family_ids = forms.CharField(max_length=100000)

    # takes a project
    def __init__(self, project, *args, **kwargs):
        super(AddFamilyGroupForm, self).__init__(*args, **kwargs)
        self.project = project

    def clean(self):
        data = self.cleaned_data
        family_ids = self.cleaned_data['family_ids'].split('|')
        data['families'] = Family.objects.filter(project=self.project, family_id__in=family_ids)
        data['family_group_slug'] = slugify(self.cleaned_data['name'])
        if data['family_group_slug'] == '':
            raise forms.ValidationError('Name is invalid: {}'.format(self.cleaned_data['name']))
        return data


class EditFamilyGroupForm(forms.Form):

    name = forms.CharField(max_length=100, label="Name of family group")
    description = forms.CharField(max_length=100, label="Short description", required=False)

    def __init__(self, project, *args, **kwargs):
        super(EditFamilyGroupForm, self).__init__(*args, **kwargs)
        self.project = project

    def clean(self):
        data = self.cleaned_data
        data['slug'] = slugify(self.cleaned_data['name'])
        if FamilyGroup.objects.filter(project=self.project, slug=data['slug']).exists():
            raise forms.ValidationError("Name is already taken")
        return data

class AddCollaboratorForm(forms.Form):
    collaborator_email = forms.EmailField(label="Collaborator's Email Address:", required=False)
    collaborator_username = forms.CharField(max_length=100, required=False)

    def clean(self):
        data = self.cleaned_data
        if data.get('collaborator_email'):
            data['collaborator_email'] = data['collaborator_email'].lower()
        elif data.get('collaborator_username'):
            data['collaborator'] = User.objects.get(username=data['collaborator_username'])
        return data


class EditCollaboratorForm(forms.Form):
    collaborator_type = forms.ChoiceField(label="Access Level", choices=COLLABORATOR_TYPES)


class EditBasicInfoForm(forms.Form):
    name = forms.CharField(label="Project Name", max_length=140, required=False)
    description = forms.CharField(widget=forms.Textarea(), required=False)


class AddTagForm(forms.Form):

    def __init__(self, project, *args, **kwargs):
        super(AddTagForm, self).__init__(*args, **kwargs)
        self.project = project

    tag = forms.CharField(max_length=50)
    title = forms.CharField(max_length=200)


class EditFamilyCauseForm(forms.Form):

    def __init__(self, family, *args, **kwargs):
        super(EditFamilyCauseForm, self).__init__(*args, **kwargs)
        self.family = family

    inheritance_mode = forms.CharField(max_length=20)  # TODO: use a ChoiceField and use it to render radio buttons in the view
