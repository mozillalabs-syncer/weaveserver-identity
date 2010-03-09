#LDAP_SERVER = 'ldaps://addressbook.mozilla.com'
#import account_ldap as account

import account_sqlite as account

import storage_peruser_sqlite
storage = storage_peruser_sqlite.WeavePerUserSQLiteStorage()

external_hostname = "localhost"
external_scheme = "http"
external_base_url = "%s://%s" % (external_scheme, external_hostname)