from datetime import datetime
import functools
import os
import re
import shutil
import sys
import traceback

import sublime
import sublime_plugin

PY3 = sys.version > '3'


## Exception Decorator                                                       ##
## ------------------------------------------------------------------------- ##
# This function allows for custom exceptions while preserving the stacktrace. #
# See discussion on Stack Overflow here: http://stackoverflow.com/a/9006442   #
## ------------------------------------------------------------------------- ##

class MissingPathException(Exception):
    pass


def catch_errors(fn):
    @functools.wraps(fn)
    def _fn(*args, **kwargs):
        try:
            return fn(*args, **kwargs)

        except MissingPathException:
            sublime.error_message("Jekyll: Unable to find path information in Jekyll.sublime-settings.")
            user_settings_path = os.path.join(sublime.packages_path(), 'User', 'Jekyll.sublime-settings')
            if not os.path.exists(user_settings_path):
                default_settings_path = os.path.join(sublime.packages_path(), 'Jekyll', 'Jekyll.sublime-settings')
                shutil.copy(default_settings_path, user_settings_path)
            sublime.active_window().open_file(user_settings_path)

        except:
            traceback.print_exc()
            sublime.error_message("Jekyll: unknown error (please, report a bug!)")

    return _fn


def get_setting(view, key, default=None):
    """
    Get a Sublime Text setting value, starting in the project-specific
    settings file, then the user-specific settings file, and finally
    the package-specific settings file. Also accepts an optional default.

    """
    try:
        settings = view.settings()
        if settings.has('Jekyll'):
            return settings.get('Jekyll').get(key)
        else:
            pass
    except:
        pass
    global_settings = sublime.load_settings('Jekyll.sublime-settings')
    return global_settings.get(key, default)


class JekyllNewPostBase(sublime_plugin.WindowCommand):
    """
    A Sublime window command base class for creating Jekyll posts.

    """
    def doCommand(self):
        self.window.show_input_panel('Jekyll post title:', '', self.title_input, None, None)

    def get_setting(self, key):
        view = self.window.active_view()
        try:
            settings = view.settings()
            if settings.has('Jekyll'):
                return settings.get('Jekyll').get(key)
            else:
                pass
        except:
            pass
        global_settings = sublime.load_settings('Jekyll.sublime-settings')
        return global_settings.get(key)

    @catch_errors
    def posts_path_string(self):
        # path = self.get_setting('posts_path')
        p = get_setting(self.window.active_view(), 'posts_path')
        if not p or p == '':
            raise MissingPathException
        return p

    @catch_errors
    def drafts_path_string(self):
        p = self.get_setting('drafts_path')
        if not p or p == '':
            raise MissingPathException
        return p

    def create_file(self, filename):
        base, filename = os.path.split(filename)
        if filename != "":
            creation_path = os.path.join(base, filename)
            open(creation_path, "a").close()

    def clean_title_input(self, title):
        POST_DATE_FORMAT = '%Y-%m-%d'
        t = title.lower()
        t_str = re.sub('[^\w\s]', '', t)
        t_str = re.sub(' |_', '-', t_str)
        d = datetime.today()
        d_str = d.strftime(POST_DATE_FORMAT)
        return d_str + '-' + t_str

    def create_post_frontmatter(self, title):
        POST_LAYOUT = self.get_setting('default_post_layout')
        POST_TITLE = title
        POST_CATEGORIES = self.get_setting('default_post_categories')
        POST_TAGS = self.get_setting('default_post_tags')
        POST_PUBLISHED = self.get_setting('default_post_published')

        frontmatter = (
            '---\n'
            'layout: {0}\n'
            'title: {1}\n'
            'published: {2}\n'
            'categories: {3}\n'
            'tags: {4}\n'
            '---\n\n'
        ).format(
            POST_LAYOUT,
            POST_TITLE,
            POST_PUBLISHED,
            POST_CATEGORIES,
            POST_TAGS,
        )
        return frontmatter

    def title_input(self, title):
        if self.IS_DRAFT:
            post_dir = self.drafts_path_string()
        else:
            post_dir = self.posts_path_string()

        syntax = self.get_setting('default_post_syntax')
        if (syntax == 'Textile'):
            file_ext = '.textile'
        else:
            file_ext = '.md'

        clean_title = self.clean_title_input(title) + file_ext
        full_path = os.path.join(post_dir, clean_title)

        if os.path.lexists(full_path):
            sublime.error_message('Jekyll: File already exists at "{0}"'.format(full_path))
            return
        else:
            frontmatter = self.create_post_frontmatter(title)
            self.create_and_open_file(full_path, frontmatter)


class JekyllListPostsBase(JekyllNewPostBase):
    """
    A subclass for displaying Jekyll posts.

    """
    def callback(self, index):
        if index > -1 and type(self.posts[index]) is list:
            f = self.posts[index][1]
            syntax = self.get_syntax(self.posts[index][0])
            output_view = self.window.open_file(f)
            output_view.set_syntax_file(
                'Packages/Jekyll/Syntaxes/{0} (Jekyll).tmLanguage'.format(syntax)
            )

    def get_syntax(self, file):
        # Uses Github preferred file extensions as referenced here: http://superuser.com/a/285878
        f = file
        if (
            f.endswith('.markdown') or
            f.endswith('.mdown') or
            f.endswith('.mkdn') or
            f.endswith('.mkd') or
            f.endswith('.md')
        ):
            self.syntax = 'Markdown'
        elif f.endswith('.textile'):
            self.syntax = 'Textile'

        return self.syntax


class JekyllOpenPostCommand(JekyllListPostsBase):
    """
    A subclass for displaying posts in the _posts directory.

    """
    posts = []
    syntax = None

    def run(self):
        path = self.posts_path_string()
        for f in os.listdir(path):
            if self.get_syntax(f) == 'Markdown' or self.get_syntax(f) == 'Textile':
                fname = os.path.splitext(f)[0]
                fpath = os.path.join(path, f)
                self.posts.append([fname, fpath])

        if not len(self.posts) > 0:
            self.posts.append('No posts found!')

        self.window.show_quick_panel(self.posts, self.callback)


class JekyllOpenDraftCommand(JekyllListPostsBase):
    """
    A subclass for displaying posts in the _drafts directory.

    """
    posts = []
    syntax = None

    def run(self):
        path = self.drafts_path_string()
        for f in os.listdir(path):
            if self.get_syntax(f) == 'Markdown' or self.get_syntax(f) == 'Textile':
                fname = os.path.splitext(f)[0]
                fpath = os.path.join(path, f)
                self.posts.append([fname, fpath])

        if not len(self.posts) > 0:
            self.posts.append('No drafts found!')

        self.window.show_quick_panel(self.posts, self.callback)


class JekyllNewPostCommand(JekyllNewPostBase):
    """
    A subclass for creating new posts

    """
    IS_DRAFT = False

    def run(self):
        self.doCommand()

    def create_and_open_file(self, path, frontmatter):
        self.create_file(path)
        view = self.window.active_view()
        view.run_command(
            'jekyll_post_frontmatter',
            args={"path": path, "frontmatter": frontmatter}
        )


class JekyllNewDraftCommand(JekyllNewPostBase):
    """
    A subclass for creating new draft posts.

    """
    IS_DRAFT = True

    def run(self):
        self.doCommand()

    def create_and_open_file(self, path, frontmatter):
        self.create_file(path)
        view = self.window.active_view()
        view.run_command(
            'jekyll_post_frontmatter',
            args={"path": path, "frontmatter": frontmatter}
        )


class JekyllPostFrontmatterCommand(sublime_plugin.TextCommand):
    """
    Creates a new post using post defaults.

    """
    def get_setting(self, key, default):
        view = self.view
        try:
            settings = view.settings()
            if settings.has('Jekyll'):
                return settings.get('Jekyll').get(key)
            else:
                pass
        except:
            pass
        global_settings = sublime.load_settings('Jekyll.sublime-settings')
        return global_settings.get(key, default)

    def run(self, edit, **args):
        path = args.get('path')
        frontmatter = args.get('frontmatter', '-there was an error-')
        syntax = self.get_setting('default_post_syntax', 'Markdown')

        output_view = self.view.window().open_file(path)

        def update():
            if output_view.is_loading():
                sublime.set_timeout_async(update, 0.1)
            else:
                output_view.run_command(
                    'insert',
                    {'characters': frontmatter}
                )
                output_view.set_syntax_file(
                    'Packages/Jekyll/Syntaxes/{0} (Jekyll).tmLanguage'.format(syntax)
                )
                output_view.run_command('save')
        update()


class JekyllInsertDateCommand(sublime_plugin.TextCommand):
    """
    Prints todays date according to format in settings file.

    """
    def get_setting(self, key, default):
        view = self.view
        try:
            settings = view.settings()
            if settings.has('Jekyll'):
                return settings.get('Jekyll').get(key)
            else:
                pass
        except:
            pass
        global_settings = sublime.load_settings('Jekyll.sublime-settings')
        return global_settings.get(key, default)

    def run(self, edit, **args):
        DEFAULT_FORMAT = '%Y-%m-%d'
        date_format = self.get_setting('insert_date_format', '%Y-%m-%d')
        datetime_format = self.get_setting('insert_datetime_format', '%Y-%m-%d %H:%M:%S')

        try:
            d = datetime.today()
            if args['format'] and args['format'] == 'date':
                text = d.strftime(date_format)
            elif args['format'] and args['format'] == 'datetime':
                text = d.strftime(datetime_format)
            else:
                text = d.strftime(DEFAULT_FORMAT)

        except Exception as e:
            sublime.error_message("Jekyll: {0}: {1}".format(type(e).__name__, e))
            return

        # Don't bother replacing selections if no text exists
        if text == '' or text.isspace():
            return

        # Do replacements
        for r in self.view.sel():
            # Insert when sel is empty to not select the contents
            if r.empty():
                self.view.insert(edit, r.a, text)
            else:
                self.view.replace(edit, r, text)