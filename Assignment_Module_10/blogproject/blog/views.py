from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Avg, Sum, Min, Max, Q
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden

from .models import BlogPost, Comment, PostLike, CommentLike, PostRating, Category
from .forms import BlogPostForm, CommentForm, PostRatingForm, RegisterForm, SearchForm


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created. Welcome!')
            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


# ---------------------------------------------------------------------------
# Home / list / detail
# ---------------------------------------------------------------------------

def home(request):
    """
    Post list annotated with engagement stats using aggregation instead of
    looping in Python. select_related('author', 'category') avoids one
    extra query per row for those two FK lookups (Section 11: BlogPost -> Author).
    """
    posts = (
        BlogPost.objects.select_related('author', 'category')
        .annotate(
            comment_count=Count('comments', distinct=True),
            like_count=Count('likes', distinct=True),
            avg_rating=Avg('ratings__rating'),
        )
        .order_by('-created_at')
    )
    paginator = Paginator(posts, 6)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'blog/home.html', {'page_obj': page_obj})


def post_detail(request, pk):
    """
    prefetch_related is used for comments/replies/likes/ratings because those
    are reverse FK / many-row relationships (Section 11: BlogPost -> Comments,
    BlogPost -> Likes, BlogPost -> Ratings) - it fetches them in a handful of
    extra queries instead of one query per related row.
    """
    post = get_object_or_404(
        BlogPost.objects.select_related('author', 'category').annotate(
            comment_count=Count('comments', distinct=True),
            like_count=Count('likes', distinct=True),
            avg_rating=Avg('ratings__rating'),
            rating_count=Count('ratings', distinct=True),
        ),
        pk=pk,
    )
    top_level_comments = (
        post.comments.filter(parent__isnull=True)
        .select_related('author')
        .prefetch_related('replies__author', 'replies__replies__author', 'likes')
        .annotate(like_count=Count('likes', distinct=True))
    )

    user_liked = False
    user_rating = None
    if request.user.is_authenticated:
        user_liked = PostLike.objects.filter(post=post, user=request.user).exists()
        user_rating = PostRating.objects.filter(post=post, user=request.user).first()

    context = {
        'post': post,
        'comments': top_level_comments,
        'comment_form': CommentForm(),
        'rating_form': PostRatingForm(instance=user_rating),
        'user_liked': user_liked,
        'user_rating': user_rating,
    }
    return render(request, 'blog/post_detail.html', context)


# ---------------------------------------------------------------------------
# Post CRUD (ownership enforced)
# ---------------------------------------------------------------------------

@login_required
def post_create(request):
    if request.method == 'POST':
        form = BlogPostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, 'Post created.')
            return redirect('post_detail', pk=post.pk)
    else:
        form = BlogPostForm()
    return render(request, 'blog/post_form.html', {'form': form, 'title': 'New Post'})


@login_required
def post_update(request, pk):
    post = get_object_or_404(BlogPost, pk=pk)
    if post.author_id != request.user.id:
        return HttpResponseForbidden("You may not edit another user's post.")
    if request.method == 'POST':
        form = BlogPostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, 'Post updated.')
            return redirect('post_detail', pk=post.pk)
    else:
        form = BlogPostForm(instance=post)
    return render(request, 'blog/post_form.html', {'form': form, 'title': 'Edit Post'})


@login_required
def post_delete(request, pk):
    post = get_object_or_404(BlogPost, pk=pk)
    if post.author_id != request.user.id:
        return HttpResponseForbidden("You may not delete another user's post.")
    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Post deleted.')
        return redirect('home')
    return render(request, 'blog/post_confirm_delete.html', {'post': post})


@login_required
def my_posts(request):
    posts = (
        BlogPost.objects.filter(author=request.user)
        .annotate(comment_count=Count('comments', distinct=True), like_count=Count('likes', distinct=True))
        .order_by('-created_at')
    )
    return render(request, 'blog/my_posts.html', {'posts': posts})


# ---------------------------------------------------------------------------
# Comments & nested replies
# ---------------------------------------------------------------------------

@login_required
def add_comment(request, pk):
    post = get_object_or_404(BlogPost, pk=pk)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            messages.success(request, 'Comment added.')
    return redirect('post_detail', pk=pk)


@login_required
def add_reply(request, pk):
    """pk is the parent Comment being replied to; the reply is saved with
    parent=that comment, which is what makes arbitrarily deep nesting work."""
    parent = get_object_or_404(Comment, pk=pk)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.post = parent.post
            reply.author = request.user
            reply.parent = parent
            reply.save()
            messages.success(request, 'Reply added.')
    return redirect('post_detail', pk=parent.post_id)


@login_required
def edit_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if comment.author_id != request.user.id:
        return HttpResponseForbidden("You may not edit another user's comment.")
    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Comment updated.')
    return redirect('post_detail', pk=comment.post_id)


@login_required
def delete_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if comment.author_id != request.user.id:
        return HttpResponseForbidden("You may not delete another user's comment.")
    post_id = comment.post_id
    if request.method == 'POST':
        comment.delete()
        messages.success(request, 'Comment deleted.')
    return redirect('post_detail', pk=post_id)


# ---------------------------------------------------------------------------
# Likes (post & comment) - toggle, unique_together prevents duplicates
# ---------------------------------------------------------------------------

@login_required
def toggle_like_post(request, pk):
    post = get_object_or_404(BlogPost, pk=pk)
    like, created = PostLike.objects.get_or_create(post=post, user=request.user)
    if not created:
        like.delete()
    return redirect('post_detail', pk=pk)


@login_required
def toggle_like_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    like, created = CommentLike.objects.get_or_create(comment=comment, user=request.user)
    if not created:
        like.delete()
    return redirect('post_detail', pk=comment.post_id)


# ---------------------------------------------------------------------------
# Ratings - create or update, never duplicate (unique_together on the model)
# ---------------------------------------------------------------------------

@login_required
def rate_post(request, pk):
    post = get_object_or_404(BlogPost, pk=pk)
    if request.method == 'POST':
        rating_value = request.POST.get('rating')
        PostRating.objects.update_or_create(
            post=post, user=request.user, defaults={'rating': rating_value}
        )
        messages.success(request, 'Rating saved.')
    return redirect('post_detail', pk=pk)


# ---------------------------------------------------------------------------
# Popular posts - pure ORM annotate + ordering, no Python-side calculation
# ---------------------------------------------------------------------------

def popular_posts(request):
    posts = (
        BlogPost.objects.select_related('author', 'category')
        .annotate(
            like_count=Count('likes', distinct=True),
            comment_count=Count('comments', distinct=True),
            avg_rating=Avg('ratings__rating'),
        )
        .order_by('-like_count', '-comment_count', '-avg_rating')[:10]
    )
    return render(request, 'blog/popular_posts.html', {'posts': posts})


# ---------------------------------------------------------------------------
# Search & filtering
# ---------------------------------------------------------------------------

def search_results(request):
    form = SearchForm(request.GET or None)
    posts = BlogPost.objects.select_related('author', 'category').annotate(
        comment_count=Count('comments', distinct=True), like_count=Count('likes', distinct=True)
    )
    query = None
    if form.is_valid():
        query = form.cleaned_data.get('q')
        category = form.cleaned_data.get('category')
        if query:
            posts = posts.filter(
                Q(title__icontains=query)
                | Q(content__icontains=query)
                | Q(author__username__icontains=query)
            )
        if category:
            posts = posts.filter(category=category)
    return render(
        request, 'blog/search_results.html', {'form': form, 'posts': posts, 'query': query}
    )


# ---------------------------------------------------------------------------
# User profile with aggregated stats
# ---------------------------------------------------------------------------

def profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    stats = User.objects.filter(pk=profile_user.pk).aggregate(
        post_count=Count('posts', distinct=True),
        comment_count=Count('comments', distinct=True),
        likes_given=Count('post_likes', distinct=True),
        ratings_given=Count('ratings_given', distinct=True),
    )
    posts = BlogPost.objects.filter(author=profile_user).annotate(
        comment_count=Count('comments', distinct=True), like_count=Count('likes', distinct=True)
    )
    return render(
        request, 'blog/profile.html', {'profile_user': profile_user, 'stats': stats, 'posts': posts}
    )


# ---------------------------------------------------------------------------
# Advanced ORM query demo page (Section 9) - shows the required lookups live
# ---------------------------------------------------------------------------

def advanced_queries_demo(request):
    examples = {
        "Posts by a specific user (author__username)": BlogPost.objects.filter(
            author__username__icontains='a'
        )[:5],
        "Posts with 'django' in the title (title__icontains)": BlogPost.objects.filter(
            title__icontains='django'
        )[:5],
        "Posts with at least 1 like (annotate + filter)": BlogPost.objects.annotate(
            like_count=Count('likes')
        ).filter(like_count__gte=1)[:5],
        "Posts with average rating >= 4 (ratings__rating__gte)": BlogPost.objects.filter(
            ratings__rating__gte=4
        ).distinct()[:5],
        "Posts with more than 1 comment (annotate + Count + filter)": BlogPost.objects.annotate(
            comment_count=Count('comments')
        ).filter(comment_count__gt=1)[:5],
    }
    # NOTE: these are deliberately kept as separate aggregate() calls, one per
    # table. Joining BlogPost -> comments AND likes AND ratings in a single
    # aggregate() causes a join "fan-out" (each related table multiplies the
    # row count), which silently inflates Count() results unless every count
    # uses distinct=True. Aggregating each relation on its own model avoids
    # the problem entirely and is the safer pattern.
    site_stats = {}
    site_stats.update(BlogPost.objects.aggregate(total_posts=Count('id')))
    site_stats.update(Comment.objects.aggregate(total_comments=Count('id')))
    site_stats.update(PostLike.objects.aggregate(total_likes=Count('id')))
    site_stats.update(
        PostRating.objects.aggregate(
            avg_rating_site_wide=Avg('rating'), min_rating=Min('rating'), max_rating=Max('rating')
        )
    )
    return render(
        request, 'blog/orm_demo.html', {'examples': examples, 'site_stats': site_stats}
    )
