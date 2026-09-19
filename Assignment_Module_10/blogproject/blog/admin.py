from django.contrib import admin
from django.db.models import Count, Avg
from .models import Category, BlogPost, Comment, PostLike, CommentLike, PostRating


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'author', 'category', 'created_at',
        'comment_count', 'like_count', 'avg_rating_display',
    )
    list_filter = ('category', 'created_at')
    search_fields = ('title', 'content', 'author__username')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _comment_count=Count('comments', distinct=True),
            _like_count=Count('likes', distinct=True),
            _avg_rating=Avg('ratings__rating'),
        )

    @admin.display(description='Comments', ordering='_comment_count')
    def comment_count(self, obj):
        return obj._comment_count

    @admin.display(description='Likes', ordering='_like_count')
    def like_count(self, obj):
        return obj._like_count

    @admin.display(description='Avg Rating', ordering='_avg_rating')
    def avg_rating_display(self, obj):
        return round(obj._avg_rating, 2) if obj._avg_rating else '-'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('post', 'author', 'parent', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('content', 'author__username')


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    list_display = ('post', 'user', 'created_at')


@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    list_display = ('comment', 'user', 'created_at')


@admin.register(PostRating)
class PostRatingAdmin(admin.ModelAdmin):
    list_display = ('post', 'user', 'rating', 'updated_at')
    list_filter = ('rating',)
