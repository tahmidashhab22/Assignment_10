from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import BlogPost, Comment, PostRating, Category


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = ['title', 'content', 'category']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 8}),
            'category': forms.Select(attrs={'class': 'form-select'}),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2, 'placeholder': 'Write a comment...'
            }),
        }


class PostRatingForm(forms.ModelForm):
    class Meta:
        model = PostRating
        fields = ['rating']
        widgets = {
            'rating': forms.Select(
                choices=[(i, f'{i} star{"s" if i > 1 else ""}') for i in range(1, 6)],
                attrs={'class': 'form-select'},
            )
        }


class SearchForm(forms.Form):
    q = forms.CharField(required=False, label='Search')
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(), required=False, empty_label='All categories'
    )
