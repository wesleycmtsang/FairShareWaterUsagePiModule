'''This Python script, memcacheClient.py, imports the Python-Memcached module to allocate local cache memory, which
   is used to backup important data in the case that Internet connection is temporarily unavailable. The backed up
   data will be uploaded to the database server once Internet connection is restored.'''
import memcache

'''The memcacheClient class creates a Memcached Client Object, which allocates local storage space of the Raspberry
   Pi as cache memory. '''
class memcacheClient(object):

    '''The init method contains several properties:
       The hostname and port, by default, is "127.0.0.1:11211", indicating the cache is set up in local memory.
       The cacheCount property indicates the number of key-value associations currently stored in local cache memory.

       In order to keep track of the number of backed up data entries, the main script will use strings of integers
       (beginning from zero) as keys to store the data entries (as values). These backed up data will be pushed back
       into the database server once Internet connection is restored.

       The cachCurr property is an integer that keeps track of the first index key at which backed up data has not
       been pushed to the database server yet.

       Thus, the cacheCount and cacheCurr properties are used to keep track of how much data is stored in cache
       memory, and how much of the backed up data have (or have not) been uploaded to the database server.'''
    def __init__(self, hostname="127.0.0.1", port="11211"):
        self.hostname = "%s:%s" %(hostname, port)
        self.connection = None
        self.cacheCount = 0
        self.cacheCurr = 0

    '''The connect method establishes the local cache memory instance.'''
    def connect(self):
        self.connection = memcache.Client([self.hostname])

    '''The valueSet method associates the key with the value and stores them in the cache memory
       as a key-value pair.'''
    def valueSet(self, key, value):
        self.connection.set(key, value)

    '''The valueGet method returns the value associated with the provided key.'''
    def valueGet(self, key):
        return self.connection.get(key)

    '''Given a particular key, the valueDelete method removes the key-value pair from cache memory.'''
    def valueDelete(self, key):
        self.connection.delete(key)

    '''The updateCacheCount method '''
    def updateCacheCount(self):
        self.cacheCount = int(self.connection.get_stats()[0][1]['curr_items'])

    '''The getCacheCount method returns the number of key-value associations currently stored in cache memory.'''
    def getCacheCount(self):
        return self.cacheCount

    '''The getCacheCurr method returns the first index in the memory cache where key-value associations
       containing backed up data exists, but have not been pushed to the database server yet.'''
    def getCacheCurr(self):
        return self.cacheCurr

    '''The cacheCountIncrement method increments the number of stored key-value associations currently stored
       in cache memory.'''
    def cacheCountIncrement(self):
        self.cacheCount += 1

    '''The cacheCurrIncrement method increments the index at which the first piece of backed up data has not
       been uploaded to the database server yet.'''
    def cacheCurrIncrement(self):
        self.cacheCurr += 1

    '''The cacheCountReset method resets the cacheCount property back to zero. The reset occurs when all the
       backed up data have been successfully pushed to the database server.'''
    def cacheCountReset(self):
        self.cacheCount = 0

    '''The cacheCountReset method resets the cacheCurr property back to zero. The reset occurs when all the
       backed up data have been successfully pushed to the database server.'''
    def cacheCurrReset(self):
        self.cacheCurr = 0
