import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from blog.models import Category, BlogPost, Comment, PostLike, CommentLike, PostRating


class Command(BaseCommand):
    help = 'Seed the database with demo users, posts, comments, likes and ratings.'

    def handle(self, *args, **options):
        random.seed(42)

        usernames = ['rahim', 'karim', 'ayesha', 'nusrat', 'imran']
        users = []
        for name in usernames:
            user, _ = User.objects.get_or_create(username=name, defaults={'email': f'{name}@example.com'})
            user.set_password('testpass123!')
            user.save()
            users.append(user)

        categories = [Category.objects.get_or_create(name=n)[0] for n in
                      ['Django', 'Python', 'Web Development', 'Databases']]

        post_data = [
            ('Django Authentication', 'How Django handles login, logout, and permissions.'),
            ('Django ORM', 'Querying the database without writing raw SQL.'),
            ('Django Model Relationships', 'ForeignKey, OneToOne, and ManyToMany explained.'),
            ('Django Forms', 'Building and validating forms the Django way.'),
            ('Getting Started with Python', 'A beginner-friendly tour of Python basics.'),
            ('REST APIs Explained', 'What REST means and why it matters for web apps.'),
            ('SQLite vs PostgreSQL', 'Choosing the right database for your project.'),
            ('select_related vs prefetch_related', 'Optimizing Django queries and avoiding N+1 problems.'),
        ]

        posts = []
        for i, (title, content) in enumerate(post_data):
            post, created = BlogPost.objects.get_or_create(
                title=title,
                defaults={
                    'content': content,
                    'author': users[i % len(users)],
                    'category': categories[i % len(categories)],
                },
            )
            posts.append(post)

        comment_bank = [
            'This was really helpful, thanks!',
            'Could you explain this in more detail?',
            'I was stuck on this for hours, great writeup.',
            'Nice explanation, straight to the point.',
            'How does this compare to the alternative approach?',
        ]

        for post in posts:
            n_comments = random.randint(1, 4)
            for _ in range(n_comments):
                author = random.choice(users)
                comment = Comment.objects.create(
                    post=post, author=author, content=random.choice(comment_bank)
                )
                # occasionally add a reply thread
                if random.random() < 0.6:
                    reply_author = random.choice([u for u in users if u != author])
                    reply = Comment.objects.create(
                        post=post, author=reply_author, parent=comment,
                        content='Good question — ' + random.choice(comment_bank).lower()
                    )
                    if random.random() < 0.4:
                        Comment.objects.create(
                            post=post, author=author, parent=reply,
                            content='Thanks, that clears it up.'
                        )

            for user in random.sample(users, k=random.randint(0, len(users))):
                PostLike.objects.get_or_create(post=post, user=user)

            for comment in post.comments.all():
                for user in random.sample(users, k=random.randint(0, 2)):
                    CommentLike.objects.get_or_create(comment=comment, user=user)

            for user in random.sample(users, k=random.randint(0, len(users))):
                PostRating.objects.get_or_create(
                    post=post, user=user, defaults={'rating': random.randint(3, 5)}
                )

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {len(users)} users, {len(posts)} posts, '
            f'{Comment.objects.count()} comments, {PostLike.objects.count()} post likes, '
            f'{PostRating.objects.count()} ratings.'
        ))
        self.stdout.write('All demo users have the password: testpass123!')
