import sys
from optparse import OptionParser

from twisted.internet import reactor
from twisted.python import usage
from flumotion.common import setup
from flumotion.inhouse.database import Connection

WRONG_TYPE = 0
CORRUPTED = 1
BAD_OUTPUT = 2
MANUAL = 3

def cbExecuteSucceeded(result):
    print "Success!"
    reactor.stop()

def cbError(error):
    return error

def cbUnknownOption(result, update):
    print "Unknown update type %r" % update
    reactor.stop()

def cbFinalError(error):
    print "Aaargh! Failure:"
    print error.value
    reactor.stop()

def connect(uri):
    conn = Connection()
    conn.open(uri)
    return conn

"""
Returns a dictionary that looks like this:
{checksum_1: [trans_id_1, trans_id_2,...],
 checksum_2: [trans_id_1, trans_id_2,...],
 ...
}
"""
def get_reports(conn, client, profile, file, checksum=None):
    def cbReportResult(result):
        dic = {}
        if result:
            for r in result:
                report_id = r[0]
                checksum = r[1]
                if checksum in dic.keys():
                    dic[checksum].append(report_id)
                else:
                    ids = [report_id]
                    dic[checksum] = ids
            return dic
        else:
            return None

    query = ("select transcoder_report_id, file_checksum" \
             " from transcoder_reports where" \
             " customer_id='%s' and profile_id='%s' and relative_path='%s'"
             ) % (client, profile, file)
    if checksum:
        query = query + " and file_checksum='%s'" % checksum

    d = conn._pool.runQuery(query)
    d.addCallback(cbReportResult)
    return d

def update_reports(ids, conn, t):
    queries = {
        WRONG_TYPE: ("update transcoder_reports set failure_id=1"\
                     " where transcoder_report_id=%s"),
        CORRUPTED: ("update transcoder_reports set failure_id=5"\
                    " where transcoder_report_id=%s"),
        BAD_OUTPUT: ("update transcoder_reports set successful=0,"\
                     " invalid_output=1"\
                     " where transcoder_report_id=%s"),
        MANUAL: ("update transcoder_reports set successful=1"\
                    " where transcoder_report_id=%s")
        }
    if t not in queries.keys():
        error =  "Ooops! Unknown query type %r" % t
        raise Exception(error)

    template = queries[t]
    print "Alright, let's do it:"
    for i in ids:
        q = template % i
        print q
        return conn.execute(q)

def pick_reports(dic, checksum=None):
    if checksum:
        if dic is None or checksum not in dic.keys():
            raise Exception("Checksum not found")
        else:
            return dic[checksum]
    elif len(dic.keys()) == 1:
        return dic[dic.keys()[0]]
    else:
        error = ("More than one file corresponds to the parameters." \
                 " Please use the -m option to choose one of the following"\
                 " checksums:")
        for k in dic.keys():
            error = error +  "\n%s" % k
        error = error + ("\n(You can use md5sum on the file you're"\
                         " dealing with)")
        raise Exception(error)

def perform_update(conn, d, type, checksum):
    choices = {'wrong-input-type': WRONG_TYPE,
               'corrupted-input': CORRUPTED,
               'manual-transcode': MANUAL,
               'bad-output': BAD_OUTPUT}
    t = choices.get(type, None)

    if t is not None:
        d.addCallbacks(pick_reports, cbError, callbackArgs=(checksum,))
        d.addCallbacks(update_reports, cbError, callbackArgs=(conn, t))
        d.addCallbacks(cbExecuteSucceeded, cbFinalError)
    else:
        d.addCallbacks(cbUnknownOption, cbFinalError,
                       callbackArgs=(type,))

class UpdateOptions(usage.Options):
    optParameters = [
        ["client", "c", None, "Name of the client who uploaded this file"],
        ["profile", "p", None,
         "Name of the profile used to transcode the file"],
        ["file", "f", None, "Name of the original file to be transcoded"],
        ["checksum", "m", None, ("Checksum of the file. Obtained by running"\
                                 " md5sum on the file (not required).")],
        ["type", "t", None,
         ("Type of update you want to perform: 'wrong-inpuy-type'"\
         ", 'corrupted-input', 'manual-transcode' or 'bad-output'.")]
    ]

class Options(usage.Options):
    subCommands = [['update', None, UpdateOptions,
                    "Update the transcoder database."]]

    optParameters = [
        ["host", "H", None, "database host (e.g. user:test@db01.priv)"],
        ["database", "d", "transcoder", "name of the database"],
        ["port", "P", 3306, "Port number to use for the database connection"]
    ]

def main(argv):

    config = Options()
    config.parseOptions()
    host, port, db = (config['host'], config['port'], config['database'])
    if host is None:
        print config
        sys.exit()

    profile, client, type, file_name, checksum = (config.subOptions['profile'],
                                                  config.subOptions['client'],
                                                  config.subOptions['type'],
                                                  config.subOptions['file'],
                                                  config.subOptions['checksum'])

    if config.subCommand == "update":
        if None in (profile, client, type, file_name):
            print config
            sys.exit()
        else:
            uri = "mysql://%s:%s/%s" % (host, port, db)
            conn = connect(uri)
            d = get_reports(conn, client, profile, file_name, checksum)
            perform_update(conn, d, type, checksum)

    reactor.run()

