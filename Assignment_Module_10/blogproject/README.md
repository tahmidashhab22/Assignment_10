# Advanced Blog Application — Module 10

Django blog app continuing the Module 9 project (auth, post CRUD, ownership)
with Module 10's model relationships and advanced ORM features layered on
top: comments with unlimited-depth nested replies, post/comment likes,
5-star ratings, aggregation/annotation-driven stats, popular posts, search
and filtering, and query optimization with `select_related` /
`prefetch_related`.

## Setup

```bash
python -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Optional — populate the database with demo users, posts, comments, likes,
and ratings so the popular-posts/search/profile pages have something to
show immediately:

```bash
python manage.py seed_demo_data
```

This creates 5 users (`rahim`, `karim`, `ayesha`, `nusrat`, `imran`, all
with password `testpass123!`) and 8 posts with randomized engagement.

Run the test suite:

```bash
python manage.py test blog
```

## Project structure

```
blogproject/        # project settings, root urls
blog/
  models.py          # Category, BlogPost, Comment, PostLike, CommentLike, PostRating
  forms.py
  views.py
  urls.py
  admin.py
  tests.py           # 14 end-to-end tests
  management/commands/seed_demo_data.py
  templates/blog/
  static/blog/css/
```

## Where each requirement lives

| Requirement | Implementation |
|---|---|
| Comments | `Comment` model, `add_comment` / `edit_comment` / `delete_comment` views |
| Nested replies | `Comment.parent` self-FK (`related_name='replies'`); rendered by the recursive `blog/comment_thread.html` partial, which includes itself for each reply |
| Post like/unlike | `PostLike` model with `unique_together = ('post', 'user')`; `toggle_like_post` view uses `get_or_create` then deletes if it already existed |
| Comment likes | `CommentLike`, same toggle pattern, `toggle_like_comment` |
| Post ratings (1–5) | `PostRating`, `unique_together = ('post', 'user')`; `rate_post` uses `update_or_create` so a second submission updates instead of duplicating |
| Aggregation/annotation | `Count`, `Avg`, `Min`, `Max` used in `home`, `post_detail`, `my_posts`, `popular_posts`, `profile`, and `/orm-demo/` |
| Popular posts | `popular_posts` view: `annotate(like_count=..., comment_count=..., avg_rating=...).order_by(...)` — no Python-side sorting |
| Search & filtering | `search_results` view: `Q(title__icontains=...) \| Q(content__icontains=...) \| Q(author__username__icontains=...)`, plus category filter |
| Advanced ORM queries | `/orm-demo/` page (`advanced_queries_demo` view) runs and displays each required lookup live: `author__username`, `title__icontains`, `likes__...`, `ratings__rating__gte`, `annotate()+Count()+filter()` |
| select_related / prefetch_related | See below |
| User profile stats | `profile` view: `User.objects.filter(pk=...).aggregate(post_count=..., comment_count=..., likes_given=..., ratings_given=...)` |
| Admin | All 6 models registered; `BlogPostAdmin` adds annotated comment/like/avg-rating columns |

## select_related() / prefetch_related() — and why

- **`select_related('author', 'category')`** is used everywhere a `BlogPost`
  queryset is built (`home`, `post_detail`, `my_posts`, `popular_posts`,
  `search_results`). Both `author` and `category` are single-valued
  forward foreign keys, so Django can pull them in with a SQL `JOIN` in the
  same query instead of issuing one extra query per post when the template
  accesses `post.author.username`.
- **`prefetch_related('replies__author', 'replies__replies__author',
  'likes')`** is used on comments in `post_detail`, because replies and
  likes are reverse, multi-row relationships — a `JOIN` would duplicate the
  parent row once per related row, so Django instead runs a small, separate
  query per relation and stitches the results together in Python. This
  avoids the N+1 query problem when the template loops over comments,
  replies, and their like counts.

### A fan-out bug found while building this (and how it was avoided)

Combining several `Count()`/`Avg()` calls across *different* joined
relations in a **single** `aggregate()` call is a common Django trap: e.g.
`BlogPost.objects.aggregate(total_comments=Count('comments'),
total_likes=Count('likes'))` joins the comments table and the likes table
in the same query, so each comment row gets multiplied by each like row
("fan-out"), silently inflating the counts. `/orm-demo/`'s site-wide stats
avoid this by aggregating each relation in its own separate `.aggregate()`
call (`BlogPost.objects.aggregate(total_posts=...)`,
`Comment.objects.aggregate(total_comments=...)`,
`PostLike.objects.aggregate(total_likes=...)`, etc.) instead of one
combined call. Where a single `annotate()` on a queryset genuinely needs
multiple `Count()`s over different relations (as in `home` and
`post_detail`), `distinct=True` is passed to every `Count()` to cancel out
the fan-out.

## Pages

Home (`/`), Post Detail (`/post/<id>/`), Create Post (`/post/new/`), Edit
Post (`/post/<id>/edit/`), Delete Post (`/post/<id>/delete/`), My Posts
(`/my-posts/`), Profile (`/profile/<username>/`), Search
(`/search/?q=...&category=...`), Popular Posts (`/popular/`), and an
ORM Demo page (`/orm-demo/`) demonstrating the required advanced queries
live.

## Notes

- Comments/likes/ratings are stored as their own related models (not plain
  text fields on `BlogPost`), per the assignment rules.
- Ownership is enforced server-side on every edit/delete view (403 if the
  requester isn't the author), and authentication is required via
  `@login_required` for anything that creates or mutates data.
- `DEBUG = True` and `ALLOWED_HOSTS = ['*']` are set for local development
  only — tighten both before any real deployment.
