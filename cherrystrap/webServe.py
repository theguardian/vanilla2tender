import os, cherrypy, urllib
import json
import simplejson
import tarfile
import shutil

from mako.template import Template
from mako.lookup import TemplateLookup
from mako import exceptions

from cherrypy.lib.static import serve_file

import threading, time

import cherrystrap

from cherrystrap import logger, formatter, database
from cherrystrap.formatter import checked



def serve_template(templatename, **kwargs):

    interface_dir = os.path.join(str(cherrystrap.PROG_DIR), 'data/interfaces/')
    template_dir = os.path.join(str(interface_dir), cherrystrap.HTTP_LOOK)

    _hplookup = TemplateLookup(directories=[template_dir])

    try:
        template = _hplookup.get_template(templatename)
        return template.render(**kwargs)
    except:
        return exceptions.html_error_template().render()


class WebInterface(object):

    def index(self):
        return serve_template(templatename="index.html", title="Home")
    index.exposed=True

    def convert(self):
        return serve_template(templatename="convert.html", title="Convert")
    convert.exposed=True

    def generateUsers(self):
        for root, dirs, files in os.walk(os.path.join(cherrystrap.DATADIR,'cache')):
            for f in files:
                os.unlink(os.path.join(root, f))
            for d in dirs:
                shutil.rmtree(os.path.join(root, d))
        try:
            myDB = database.DBConnection()
            pass
        except:
            logger.info("There was a MySQL connection error.  Please check your Vanilla MySQL connection credentials")
            return serve_template(templatename="index.html")

        JSONDIR = os.path.join(cherrystrap.DATADIR,'cache','users')
        if not os.path.exists(JSONDIR):
            try:
                os.makedirs(JSONDIR)
            except OSError:
                logger.error('Could not create user director. Check permissions of: ' + cherrystrap.DATADIR)
        
        userInfo=[]
        userCount = 0
        support_users = ([support_user.strip() for support_user in cherrystrap.VANILLA_SUPPORT.split(',')])
        users = myDB.select("SELECT * FROM %s" % cherrystrap.VANILLA_DB+'.GDN_User')
        for user in users:
            userCount += 1
            if user['Name'] in support_users:
                user_state = "support"
            else:
                user_state = "user"
            userInfo = {
                "name": user['Name'],
                "email": user['Email'],
                "title": "",
                "created_at": user['DateInserted'].strftime('%Y-%m-%dT%H:%M:%SZ'),
                "state": user_state,
                "password": "secret"
                }
            OUTDIR = os.path.join(JSONDIR,str(userCount)+'.json')
            with open(OUTDIR, 'w') as outfile:
                json.dump(userInfo, outfile)

    generateUsers.exposed=True

    def generateCategories(self):
        try:
            myDB = database.DBConnection()
            pass
        except:
            logger.info("There was a MySQL connection error.  Please check your Vanilla MySQL connection credentials")
            return serve_template(templatename="index.html")

        JSONDIR = os.path.join(cherrystrap.DATADIR,'cache','categories')
        if not os.path.exists(JSONDIR):
            try:
                os.makedirs(JSONDIR)
            except OSError:
                logger.error('Could not create user director. Check permissions of: ' + cherrystrap.DATADIR)
        
        categoryInfo=[]
        categoryCount = 0
        categories = myDB.select("SELECT * FROM %s" % cherrystrap.VANILLA_DB+'.GDN_Category')
        for category in categories:
            if category['Name'] != 'Root':
                categoryCount += 1
                categoryID = category['CategoryID']
                
                CATDIR = os.path.join(cherrystrap.DATADIR,'cache','categories',str(categoryID))
                if not os.path.exists(CATDIR):
                    try:
                        os.makedirs(CATDIR)
                    except OSError:
                        logger.error('Could not create user director. Check permissions of: ' + cherrystrap.DATADIR)

                categoryInfo = {
                    "name": category['Name'],
                    "summary": category['Description']
                    }
                OUTDIR = os.path.join(JSONDIR,str(categoryID)+'.json')
                with open(OUTDIR, 'w') as outfile:
                    json.dump(categoryInfo, outfile)

    generateCategories.exposed=True

    def generateDiscussions(self):
        try:
            myDB = database.DBConnection()
            pass
        except:
            logger.info("There was a MySQL connection error.  Please check your Vanilla MySQL connection credentials")
            return serve_template(templatename="index.html")

        JSONDIR = os.path.join(cherrystrap.DATADIR,'cache','categories')
        if not os.path.exists(JSONDIR):
            try:
                os.makedirs(JSONDIR)
            except OSError:
                logger.error('Could not create user director. Check permissions of: ' + cherrystrap.DATADIR)
        
        discussionInfo=[]
        discussionCount = 0
        discussions = myDB.select("SELECT * FROM %s" % cherrystrap.VANILLA_DB+'.GDN_Discussion')
        for discussion in discussions:
            discussionCount += 1

            categoryID = discussion['CategoryID']
            discussionID = discussion['DiscussionID']
            posterID = discussion['InsertUserID']
            findUser = myDB.select("SELECT * FROM %s WHERE UserID = %s" % (cherrystrap.VANILLA_DB+'.GDN_User', posterID))
            for user in findUser:
                posterEmail = user['Email']

            commentsInfo = []
            #ORIGINAL POSTER
            commentsInfo.append({
                "author_email": posterEmail,
                "created_at": discussion['DateInserted'].strftime('%Y-%m-%dT%H:%M:%SZ'),
                "body": discussion['Body']
                })

            comments = myDB.select("SELECT * FROM %s WHERE DiscussionID = %s" % (cherrystrap.VANILLA_DB+'.GDN_Comment', discussionID))
            for comment in comments:
                commentUserID = comment['InsertUserID']
                commentCreated = comment['DateInserted'].strftime('%Y-%m-%dT%H:%M:%SZ')
                commentBody = comment['Body']
                findCommenter = myDB.select("SELECT * FROM %s WHERE UserID = %s" % (cherrystrap.VANILLA_DB+'.GDN_User', commentUserID))
                for commenter in findCommenter:
                    commentEmail = commenter['Email']

                commentsInfo.append({
                "author_email": commentEmail,
                "created_at": commentCreated,
                "body": commentBody
                })

            discussionInfo = {
                "title": discussion['Name'],
                "author_email": posterEmail,
                "created_at": discussion['DateInserted'].strftime('%Y-%m-%dT%H:%M:%SZ'),
                "comments": commentsInfo
                }

            OUTDIR = os.path.join(JSONDIR,str(categoryID),str(discussionID)+'.json')
            with open(OUTDIR, 'w') as outfile:
                json.dump(discussionInfo, outfile)

    generateDiscussions.exposed=True

    def downloadZip(self):
        tar = tarfile.open("vanilla2tender.tar.gz", "w:gz")
        tar.add(os.path.join(cherrystrap.DATADIR,'cache'), arcname="vanilla2tender")
        tar.close()

        return serve_file(os.path.join(cherrystrap.DATADIR, "vanilla2tender.tar.gz"), "application/x-download", "attachment")
    downloadZip.exposed=True

    def config(self):
        http_look_dir = os.path.join(cherrystrap.PROG_DIR, 'data/interfaces/')
        http_look_list = [ name for name in os.listdir(http_look_dir) if os.path.isdir(os.path.join(http_look_dir, name)) ]

        config = {
                    "server_name":      cherrystrap.SERVER_NAME,
                    "http_host":        cherrystrap.HTTP_HOST,
                    "http_user":        cherrystrap.HTTP_USER,
                    "http_port":        cherrystrap.HTTP_PORT,
                    "http_pass":        cherrystrap.HTTP_PASS,
                    "http_look":        cherrystrap.HTTP_LOOK,
                    "http_look_list":   http_look_list,
                    "launch_browser":   checked(cherrystrap.LAUNCH_BROWSER),
                    "logdir":           cherrystrap.LOGDIR,
                    "vanilla_host":        cherrystrap.VANILLA_HOST,
                    "vanilla_port":        cherrystrap.VANILLA_PORT,
                    "vanilla_user":        cherrystrap.VANILLA_USER,
                    "vanilla_password":    cherrystrap.VANILLA_PASSWORD,
                    "vanilla_db":    cherrystrap.VANILLA_DB,
                    "vanilla_support":    cherrystrap.VANILLA_SUPPORT
                }
        return serve_template(templatename="config.html", title="Settings", config=config)    
    config.exposed = True

    def configUpdate(self, server_name="Vanilla2Tender", http_host='0.0.0.0', http_user=None, http_port=7949, http_pass=None, http_look=None, launch_browser=0, logdir=None, 
        vanilla_host=None, vanilla_port=None, vanilla_user=None, vanilla_password=None, vanilla_db=None, vanilla_support=None):

        cherrystrap.SERVER_NAME = server_name
        cherrystrap.HTTP_HOST = http_host
        cherrystrap.HTTP_PORT = http_port
        cherrystrap.HTTP_USER = http_user
        cherrystrap.HTTP_PASS = http_pass
        cherrystrap.HTTP_LOOK = http_look
        cherrystrap.LAUNCH_BROWSER = launch_browser
        cherrystrap.LOGDIR = logdir

        cherrystrap.VANILLA_HOST = vanilla_host
        cherrystrap.VANILLA_PORT = vanilla_port
        cherrystrap.VANILLA_USER = vanilla_user
        cherrystrap.VANILLA_PASSWORD = vanilla_password
        cherrystrap.VANILLA_DB = vanilla_db
        cherrystrap.VANILLA_SUPPORT = vanilla_support

        cherrystrap.config_write()
        logger.info("Configuration saved successfully")

    configUpdate.exposed = True

    def logs(self):
         return serve_template(templatename="logs.html", title="Log", lineList=cherrystrap.LOGLIST)
    logs.exposed = True

    def getLog(self,iDisplayStart=0,iDisplayLength=100,iSortCol_0=0,sSortDir_0="desc",sSearch="",**kwargs):

        iDisplayStart = int(iDisplayStart)
        iDisplayLength = int(iDisplayLength)

        filtered = []
        if sSearch == "":
            filtered = cherrystrap.LOGLIST[::]
        else:
            filtered = [row for row in cherrystrap.LOGLIST for column in row if sSearch in column]

        sortcolumn = 0
        if iSortCol_0 == '1':
            sortcolumn = 2
        elif iSortCol_0 == '2':
            sortcolumn = 1
        filtered.sort(key=lambda x:x[sortcolumn],reverse=sSortDir_0 == "desc")

        rows = filtered[iDisplayStart:(iDisplayStart+iDisplayLength)]
        rows = [[row[0],row[2],row[1]] for row in rows]

        dict = {'iTotalDisplayRecords':len(filtered),
                'iTotalRecords':len(cherrystrap.LOGLIST),
                'aaData':rows,
                }
        s = simplejson.dumps(dict)
        return s
    getLog.exposed = True

    def template_reference(self):
        return serve_template(templatename="template.html", title="Template Reference")
    template_reference.exposed=True

    def shutdown(self):
        cherrystrap.config_write()
        cherrystrap.SIGNAL = 'shutdown'
        message = 'shutting down ...'
        return serve_template(templatename="shutdown.html", title="Exit", message=message, timer=10)
        return page
    shutdown.exposed = True

    def restart(self):
        cherrystrap.SIGNAL = 'restart'
        message = 'restarting ...'
        return serve_template(templatename="shutdown.html", title="Restart", message=message, timer=10)
    restart.exposed = True