#!/usr/bin/env python

import os
import sys
import cmd
import git
import re
import tempfile
import ConfigParser
from subprocess import call

config = ConfigParser.ConfigParser()
config.read("/home/noqqe/.cmddocsrc")
datadir = config.get("General", "Datadir")
exclude = config.get("General", "Excludedir")
default_commit_msg = config.get("General", "Default_Commit_Message")

try:
    os.chdir(datadir)
except OSError:
    print "Error: Datadir %s does not exist" % datadir

if os.environ.get('EDITOR') is None:
    print "Error: EDITOR not set in environment"
    print "Try running: export EDITOR=$(which vim)"
    exit(1)

if os.environ.get('PAGER') is None:
    print "Error: PAGER not set in environment"
    print "Try running: export PAGER=$(which less)"
    exit(1)

if not os.path.isdir(datadir):
    print "Error: Your Datadir %s does not exist" % datadir
    print "Create it or edit your config in ~/.cmddocsrc"
    exit(1)


try:
    repo = git.Repo(datadir)
except git.exc.InvalidGitRepositoryError:
    repo = git.Repo.init(datadir)
    repo.git.add(".")
    repo.git.commit("init")
    print("Successfully created and initialized empty repo at " % datadir)

def list_articles(dir):
    d = os.path.relpath(os.getcwd(),dir)
    call(["tree", d ])

def list_directories(dir):
    d = os.path.relpath(os.getcwd(),dir)
    call(["tree", "-d", d ])

def change_directory(dir):
    """ switch directory within docs dir """
    d = os.path.join(os.getcwd(),dir)

    # dont cd out of datadir
    if not datadir in d:
        d = datadir

    # if empty, switch to datadir
    if not dir:
        d = datadir

    # switch to dir
    try:
        os.chdir(d)
    except OSError:
        print("Directory %s not found" % dir)

def edit_article(article,dir):
    # set paths
    a = os.path.join(dir,article)
    d = os.path.dirname(a)

    # create dir(s)
    if not os.path.isdir(d):
        os.makedirs(d)

    # start editor
    os.system('%s %s' % (os.getenv('EDITOR'),a))

    # commit into git
    try:
        repo.git.add(a)
        if repo.is_dirty():
            msg = raw_input("Commit message: ")
            if not msg: 
                msg = default_commit_msg
            repo.git.commit(m=msg)
        else:
            print "Nothing to commit"
    except:
        pass

def view_article(article,dir):
    a = os.path.join(dir,article)
    article = open(a, "r")
    content = article.read()
    article.close()
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        h = re.compile('^#{3,5}\s*(.*)\ *$',re.MULTILINE)
        content = h.sub('\033[1m\033[37m\\1\033[0m', content)
        h = re.compile('^#{1,2}\s*(.*)\ *$',re.MULTILINE)
        content = h.sub('\033[4m\033[1m\033[37m\\1\033[0m', content)
        h = re.compile('^\ {4}(.*)',re.MULTILINE)
        content = h.sub('\033[92m\\1\033[0m', content)
        h = re.compile('~~~\s*([^~]*)~~~[^\n]*\n',re.DOTALL)
        content = h.sub('\033[92m\\1\033[0m', content)
        tmp.write(content)

    # start editor
    os.system('%s -r %s' % (os.getenv('PAGER'),tmp.name))
    try:
        os.remove(tmp.name)
    except OSError:
        print "Error: Could not remove %s" % tmp.name

def delete_article(article,dir):
    a = os.path.join(dir,article)
    try:
        repo.git.rm(a)
        repo.git.commit(m="%s deleted" % article)
    except:
        if os.path.isdir(a):
            os.rmdir(a)
            print("Removed directory %s which was not under version control" % a)
        else:
            os.remove(a)
            print("Removed file %s which was not under version control" % a)

    return "%s deleted" % article

def move_article(dir,args):
    args = args.split()
    if len(args)!=2:
        print "Invalid usage\nUse: mv source dest"
        return

    a = os.path.join(dir,args[0])
    e = os.path.join(dir,args[1])
    d = os.path.dirname(e)

    # create dir(s)
    if not os.path.isdir(d):
        os.makedirs(d)

    # move file in git and commit
    repo.git.mv(a,e)
    repo.git.commit(m="Moved %s to %s" % (article,dest))
    return "Moved %s to %s" % (article,dest)

def search_article(keyword,dir):
    c = 0
    r = re.compile(keyword)
    for dirpath, dirs, files in os.walk(dir):
        dirs[:] = [d for d in dirs if d not in exclude]
        for fname in files:
            path = os.path.join(dirpath, fname)
            f = open(path, "rt")
            for i, line in enumerate(f):
                if r.search(line):
                    c = c + 1
                    print "* \033[92m%s\033[39m: %s" % (os.path.relpath(path, datadir),
                            line.rstrip('\n'))
    return "Results: %s" % c

def show_log(args):
    args = args.split()
    format="format:%C(blue)%h %Cgreen%C(bold)%ad %Creset%s"
    dateformat="short"

    if len(args) >= 1:
        if os.path.isfile(os.path.join(os.getcwd(), args[0])):
            file = args[0]
            try:
                count = args[1]
                print "Last %s commits for %s" % (count, file)
                print repo.git.log(file, pretty=format, n=count, date=dateformat)
            except IndexError:
                count = 10
                print "Last %s commits for %s" % (count, file)
                print repo.git.log(file, pretty=format, n=count, date=dateformat)
        else:
            count = args[0]
            try:
                file = args[1]
                print "Last %s commits for %s" % (count, file)
                print repo.git.log(file, pretty=format, n=count, date=dateformat)
            except IndexError:
                print "Last %s commits" % count
                print repo.git.log(pretty=format, n=count, date=dateformat)

    elif len(args) == 0:
        count = 10
        print "Last %s commits" % count
        print repo.git.log(pretty=format, n=count,date=dateformat)

def path_complete(self, text, line, begidx, endidx):
    arg = line.split()[1:]

    if not arg:
        completions = os.listdir('./')
        completions[:] = [d for d in completions if d not in exclude]
    else:
        dir, part, base = arg[-1].rpartition('/')
        if part == '':
            dir = './'
        elif dir == '':
            dir = '/'

        completions = []
        for f in os.listdir(dir):
            if f.startswith(base):
                if os.path.isfile(os.path.join(dir,f)):
                    completions.append(f)
                else:
                    completions.append(f+'/')
    return completions

class Prompt(cmd.Cmd):
    """ Basic commandline interface class """

    prompt = "\033[1m\033[37mcmddocs> \033[0m"
    intro = "Welcome to cmddocs"

    ### list
    def do_list(self, cwd):
        """
        Show files in current working dir

        """
        try:
            cwd
        except NameError:
            cwd = os.getcwd()
        return list_articles(cwd)

    def complete_list(self, text, line, begidx, endidx):
        return path_complete(self, text, line, begidx, endidx)

    def do_l(self, cwd):
        "Show files in current working dir"
        try:
            cwd
        except NameError:
            cwd = os.getcwd()
        return list_articles(cwd)

    def do_view(self, article):
        "Show files in current working dir"
        try:
            cwd
        except NameError:
            cwd = os.getcwd()
        return view_article(article, cwd)

    def do_ls(self, cwd):
        "Show files in current working dir"
        try:
            cwd
        except NameError:
            cwd = os.getcwd()
        return list_articles(cwd)

    def do_d(self, cwd):
        "Show only directories in current working dir"
        try:
            cwd
        except NameError:
            cwd = os.getcwd()
        return list_directories(cwd)

    def do_dirs(self, cwd):
        "Show only directories in current working dir"
        try:
            cwd
        except NameError:
            cwd = os.getcwd()
        return list_directories(cwd)

    def complete_l(self, text, line, begidx, endidx):
        return path_complete(self, text, line, begidx, endidx)

    def complete_view(self, text, line, begidx, endidx):
        return path_complete(self, text, line, begidx, endidx)

    def complete_ls(self, text, line, begidx, endidx):
        return path_complete(self, text, line, begidx, endidx)

    def do_cd(self,dir):
        "Change directory"
        return change_directory(dir)

    def complete_cd(self, text, line, begidx, endidx):
        return path_complete(self, text, line, begidx, endidx)

    def do_pwd(self,line):
        "Show current directory"
        print os.path.relpath(os.getcwd(),datadir)

    ### edit
    def do_edit(self, article):
        "Edit an article. edit path/to/article"
        return edit_article(article, os.getcwd())

    def complete_edit(self, text, line, begidx, endidx):
        return path_complete(self, text, line, begidx, endidx)

    def do_e(self, article):
        "Edit an article. e path/to/article"
        return edit_article(article, os.getcwd())

    def complete_e(self, text, line, begidx, endidx):
        return path_complete(self, text, line, begidx, endidx)

    ### delete
    def do_delete(self, article):
        "Delete an article"
        delete_article(article, os.getcwd())

    def complete_delete(self, text, line, begidx, endidx):
        return path_complete(self, text, line, begidx, endidx)

    def do_rm(self, article):
        "Delete an article"
        delete_article(article, os.getcwd())

    def complete_rm(self, text, line, begidx, endidx):
        return path_complete(self, text, line, begidx, endidx)

    ### move
    def do_move(self, line):
        "Move an article"
        args = line.split()
        if len(args)!=2:
            print "Invalid usage\nUse: move source dest"
            return
        move_article(os.getcwd(),args)

    def complete_move(self, text, line, begidx, endidx):
        return path_complete(self, text, line, begidx, endidx)

    def do_mv(self, line):
        "Move an article"
        move_article(os.getcwd(),args)

    def complete_mv(self, text, line, begidx, endidx):
        return path_complete(self, text, line, begidx, endidx)

    ### search
    def do_search(self, keyword):
        "Search for keyword in current directory. Example: search mongodb"
        print search_article(keyword,os.getcwd())

    ### misc
    def do_status(self, line):
        "Show git repo status of your docs"
        repo.git.status()

    def do_log(self, args):
        """
        Show git logs of your docs.

        Usage: log              # default loglines: 10)
               log 20           # show 20 loglines
               log 20 article   # show log for specific article
        """
        show_log(args)

    def complete_log(self, text, line, begidx, endidx):
        return path_complete(self, text, line, begidx, endidx)

    ### exit
    def do_exit(self, line):
        "Exit cmddocs"
        return True

    def do_EOF(self, line):
        "Exit cmddocs"
        print "exit"
        return True


if __name__ == '__main__':
    Prompt().cmdloop()
