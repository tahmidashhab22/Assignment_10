from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('popular/', views.popular_posts, name='popular_posts'),
    path('search/', views.search_results, name='search_results'),
    path('orm-demo/', views.advanced_queries_demo, name='orm_demo'),

    path('my-posts/', views.my_posts, name='my_posts'),
    path('profile/<str:username>/', views.profile, name='profile'),

    path('post/new/', views.post_create, name='post_create'),
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('post/<int:pk>/edit/', views.post_update, name='post_update'),
    path('post/<int:pk>/delete/', views.post_delete, name='post_delete'),
    path('post/<int:pk>/like/', views.toggle_like_post, name='toggle_like_post'),
    path('post/<int:pk>/rate/', views.rate_post, name='rate_post'),
    path('post/<int:pk>/comment/', views.add_comment, name='add_comment'),

    path('comment/<int:pk>/reply/', views.add_reply, name='add_reply'),
    path('comment/<int:pk>/edit/', views.edit_comment, name='edit_comment'),
    path('comment/<int:pk>/delete/', views.delete_comment, name='delete_comment'),
    path('comment/<int:pk>/like/', views.toggle_like_comment, name='toggle_like_comment'),

    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
