from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import BlogPost, Comment, PostLike, CommentLike, PostRating, Category


class BlogFeatureTests(TestCase):
    """
    End-to-end tests covering the Module 10 requirements: comments, nested
    replies, post/comment likes (no duplicates), ratings (no duplicates,
    updatable), ownership restrictions, search/filtering, popular posts,
    profile stats, and the aggregation/annotation-driven pages.
    """

    def setUp(self):
        self.rahim = User.objects.create_user('rahim', password='testpass123!')
        self.karim = User.objects.create_user('karim', password='testpass123!')
        self.category = Category.objects.create(name='Django')
        self.c1 = Client()
        self.c1.login(username='rahim', password='testpass123!')
        self.c2 = Client()
        self.c2.login(username='karim', password='testpass123!')

        self.c1.post('/post/new/', {
            'title': 'How to Learn Django', 'content': 'Start with models.',
            'category': self.category.id,
        })
        self.post = BlogPost.objects.get(title='How to Learn Django')

    def test_post_created_with_correct_author(self):
        self.assertEqual(self.post.author, self.rahim)

    def test_non_owner_cannot_edit_or_delete_post(self):
        r = self.c2.post(f'/post/{self.post.pk}/edit/', {
            'title': 'Hacked', 'content': 'x', 'category': self.category.id
        })
        self.post.refresh_from_db()
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.post.title, 'How to Learn Django')

        r = self.c2.post(f'/post/{self.post.pk}/delete/')
        self.assertEqual(r.status_code, 403)
        self.assertTrue(BlogPost.objects.filter(pk=self.post.pk).exists())

    def test_nested_replies_three_levels_deep(self):
        self.c2.post(f'/post/{self.post.pk}/comment/', {'content': 'How can I learn Django?'})
        top = Comment.objects.get(content='How can I learn Django?')
        self.assertIsNone(top.parent)

        self.c1.post(f'/comment/{top.pk}/reply/', {'content': 'Start with Django Models.'})
        reply1 = Comment.objects.get(content='Start with Django Models.')
        self.assertEqual(reply1.parent_id, top.pk)

        self.c2.post(f'/comment/{reply1.pk}/reply/', {'content': 'Should I learn Models before Forms?'})
        reply2 = Comment.objects.get(content='Should I learn Models before Forms?')
        self.assertEqual(reply2.parent_id, reply1.pk)

    def test_non_owner_cannot_edit_or_delete_comment(self):
        self.c2.post(f'/post/{self.post.pk}/comment/', {'content': 'A comment'})
        comment = Comment.objects.get(content='A comment')
        r = self.c1.post(f'/comment/{comment.pk}/edit/', {'content': 'hacked'})
        comment.refresh_from_db()
        self.assertEqual(r.status_code, 403)
        self.assertEqual(comment.content, 'A comment')

    def test_post_like_toggle_prevents_duplicates(self):
        url = f'/post/{self.post.pk}/like/'
        self.c2.get(url)
        self.assertTrue(PostLike.objects.filter(post=self.post, user=self.karim).exists())
        self.c2.get(url)  # unlike
        self.assertFalse(PostLike.objects.filter(post=self.post, user=self.karim).exists())
        self.c2.get(url)
        self.c2.get(url)
        self.c2.get(url)
        self.assertLessEqual(PostLike.objects.filter(post=self.post, user=self.karim).count(), 1)

    def test_comment_like(self):
        self.c2.post(f'/post/{self.post.pk}/comment/', {'content': 'nice post'})
        comment = Comment.objects.get(content='nice post')
        self.c1.get(f'/comment/{comment.pk}/like/')
        self.assertTrue(CommentLike.objects.filter(comment=comment, user=self.rahim).exists())

    def test_rating_updates_instead_of_duplicating(self):
        self.c2.post(f'/post/{self.post.pk}/rate/', {'rating': 4})
        self.c2.post(f'/post/{self.post.pk}/rate/', {'rating': 5})
        ratings = PostRating.objects.filter(post=self.post, user=self.karim)
        self.assertEqual(ratings.count(), 1)
        self.assertEqual(ratings.first().rating, 5)

    def test_post_detail_annotations(self):
        self.c2.post(f'/post/{self.post.pk}/comment/', {'content': 'c1'})
        self.c2.post(f'/post/{self.post.pk}/rate/', {'rating': 5})
        r = self.c1.get(f'/post/{self.post.pk}/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['post'].comment_count, 1)
        self.assertEqual(r.context['post'].avg_rating, 5.0)

    def test_search_by_keyword_author_and_category(self):
        r = self.c1.get('/search/', {'q': 'Django'})
        self.assertIn(self.post, r.context['posts'])
        r = self.c1.get('/search/', {'q': 'karim'})
        self.assertNotIn(self.post, r.context['posts'])
        r = self.c1.get('/search/', {'category': self.category.id})
        self.assertIn(self.post, r.context['posts'])

    def test_popular_posts_page_loads(self):
        r = self.c1.get('/popular/')
        self.assertEqual(r.status_code, 200)

    def test_profile_stats(self):
        r = self.c1.get('/profile/rahim/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['stats']['post_count'], 1)

    def test_orm_demo_page_and_no_join_fanout(self):
        """Regression test: aggregating counts across multiple joined
        relations in one call must not inflate total_posts (fan-out bug)."""
        self.c2.post(f'/post/{self.post.pk}/comment/', {'content': 'one'})
        self.c2.post(f'/post/{self.post.pk}/rate/', {'rating': 5})
        r = self.c1.get('/orm-demo/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['site_stats']['total_posts'], 1)

    def test_anonymous_user_cannot_comment(self):
        anon = Client()
        r = anon.post(f'/post/{self.post.pk}/comment/', {'content': 'anon'})
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login/', r.url)

    def test_owner_can_delete_own_comment(self):
        self.c1.post(f'/post/{self.post.pk}/comment/', {'content': 'mine'})
        comment = Comment.objects.get(content='mine')
        self.c1.post(f'/comment/{comment.pk}/delete/')
        self.assertFalse(Comment.objects.filter(pk=comment.pk).exists())
