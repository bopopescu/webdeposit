# -*- coding: utf-8 -*-
##
## This file is part of Invenio.
## Copyright (C) 2013 CERN.
##
## Invenio is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## Invenio is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Invenio; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

import os
import sys

from invenio.scriptutils import Manager

manager = Manager(usage="Perform demosite operations")

# Shortcuts for manager options to keep code DRY.
option_yes_i_know = manager.option('--yes-i-know', action='store_true',
                                   dest='yes_i_know', help='use with care!')
option_default_data = manager.option('--no-data', action='store_false',
                                     dest='default_data',
                                     help='do not populate tables with default data')


@option_default_data
def populate(default_data=True):
    """Load demo records.  Useful for testing purposes."""
    from invenio.config import CFG_PREFIX
    from invenio.sqlalchemyutils import db
    print ">>> Going to load demo records..."
    db.session.execute("TRUNCATE schTASK")
    db.session.commit()
    for cmd in ["%s/bin/bibupload -u admin -i %s/var/tmp/demobibdata.xml" % (CFG_PREFIX, CFG_PREFIX),
                "%s/bin/bibupload 1" % CFG_PREFIX,
                "%s/bin/bibdocfile --textify --with-ocr --recid 97" % CFG_PREFIX,
                "%s/bin/bibdocfile --textify --all" % CFG_PREFIX,
                "%s/bin/bibindex -u admin" % CFG_PREFIX,
                "%s/bin/bibindex 2" % CFG_PREFIX,
                "%s/bin/bibreformat -u admin -o HB" % CFG_PREFIX,
                "%s/bin/bibreformat 3" % CFG_PREFIX,
                "%s/bin/webcoll -u admin" % CFG_PREFIX,
                "%s/bin/webcoll 4" % CFG_PREFIX,
                "%s/bin/bibrank -u admin" % CFG_PREFIX,
                "%s/bin/bibrank 5" % CFG_PREFIX,
                "%s/bin/bibsort -u admin -R" % CFG_PREFIX,
                "%s/bin/bibsort 6" % CFG_PREFIX,
                "%s/bin/oairepositoryupdater -u admin" % CFG_PREFIX,
                "%s/bin/oairepositoryupdater 7" % CFG_PREFIX,
                "%s/bin/bibupload 8" % CFG_PREFIX, ]:
        if os.system(cmd):
            print "ERROR: failed execution of", cmd
            sys.exit(1)
    print ">>> Demo records loaded successfully."


@manager.command
def create(data='demosite'):
    """Populate database with demo site data."""

    from invenio.sqlalchemyutils import db
    from invenio.config import CFG_PREFIX
    from invenio.websession_model import User
    from invenio.config_manager import get_conf

    print ">>> Going to create demo site..."
    db.session.execute("TRUNCATE schTASK")
    db.session.execute("TRUNCATE session")
    User.query.filter(User.email == '').delete()
    db.session.commit()

    from invenio.database_manager import load_fixtures
    load_fixtures(suffix=data, truncate_tables_first=True)

    db.session.execute("UPDATE idxINDEX SET stemming_language='en' WHERE name IN ('global','abstract','keyword','title','fulltext');")
    db.session.commit()

    conf = get_conf()

    from invenio.inveniocfg import cli_cmd_reset_sitename, \
        cli_cmd_reset_siteadminemail, cli_cmd_reset_fieldnames

    cli_cmd_reset_sitename(conf)
    cli_cmd_reset_siteadminemail(conf)
    cli_cmd_reset_fieldnames(conf)  # needed for I18N demo ranking method names

    for cmd in ["%s/bin/webaccessadmin -u admin -c -r -D" % CFG_PREFIX,
                "%s/bin/webcoll -u admin" % CFG_PREFIX,
                "%s/bin/webcoll 1" % CFG_PREFIX,
                "%s/bin/bibsort -u admin --load-config" % CFG_PREFIX,
                "%s/bin/bibsort 2" % CFG_PREFIX, ]:
        if os.system(cmd):
            print "ERROR: failed execution of", cmd
            sys.exit(1)
    print ">>> Demo site created successfully."


def main():
    from invenio.webinterface_handler_flask import create_invenio_flask_app
    app = create_invenio_flask_app()
    manager.app = app
    manager.run()

if __name__ == '__main__':
    main()
