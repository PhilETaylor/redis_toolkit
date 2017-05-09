import redis
import os

import cPickle as pickle

from argparse import ArgumentParser, RawTextHelpFormatter
from collections import defaultdict, Counter
from prefixtree import Node


class MemoryReportNode(Node):
    """Extending the Node class with some custom attributes specific to the hit rate only."""

    def __init__(self, key):

        # The number of GET operations.
        #Node.get = 0

        # The number of SET operations
        #Node.set = 0

        # The key size. Non-leaf nodes have a total size calculated as the sum of all sizes.
        Node.size = 0

        # The number of keys that actually have a size value. Useful for an accurate average key size.
        #Node.size_count = 0

        # The life time defined as the time between 2 consecutive sets.
        #Node.lifetime = 0

        # The number of keys that actually have a lifetime value. Useful for an accurate average life time.
        #Node.lifetime_count = 0

        super(MemoryReportNode, self).__init__(key)

    def populate(self, node=None):
        """
        Populates the nodes with the data (nr. of gets, sets, hitrate, avg size, lifetime) from the local redis.
        @return a tuple (leaf_count, nr. of gets, nr. of sets)
        """
        if node == None: node = self

        for i, child in enumerate(node.children):
            if child.is_leaf():
                # This is where I query Redis for the key information (gets, set, hitrate, etc).
                size = redis_get_size(child.key)

                #print len(data)
                #print data
                #return
                
                child.leaf_count = 1
                child.size       = size

                #try: 
                    #child.get  = int(data['get'])
                    #child.set  = int(data['set'])
                    # Only leaf nodes have fixed sizes and lifetimes (directly from Redis).
                    #child.size = size
                    #child.lifetime = float(data['lifetime'])
                #except KeyError:
                    #pass
                    # Sometimes not all the keys are set ... Just using defaults.
                #    sys.stderr.write('Error on line {}. {}, {}'.format(sys.exc_info()[-1].tb_lineno, type(e), e))

                # For average calculation.
                #if child.size > 0:
                #    child.size_count = 1

                #if child.lifetime > 0:
                #    child.lifetime_count = 1

                # Increment leaf count.
                node.leaf_count += 1

                # Increment the number of gets and sets.
                #node.get += child.get
                #node.set += child.set

                # Increment the total size and size_count.
                node.size += child.size
                #if child.size > 0:
                #    node.size_count += 1

                #node.lifetime += child.lifetime
                #if child.lifetime > 0:
                #    node.lifetime_count += 1

            else:
                obj = self.populate(child)
                
                node.leaf_count += obj['leaf_count']

                #node.get += obj['get']
                #node.set += obj['set']

                node.size += obj['size']
                #node.size_count += obj['size_count']

                #node.lifetime       += float(obj['lifetime'])
                #node.lifetime_count += obj['lifetime_count']

        return {
            'leaf_count': node.leaf_count,
            #'get': node.get,
            #'set': node.set,
            'size': node.size
            #'size_count': node.size_count,
            #'lifetime': node.lifetime,
            #'lifetime_count': node.lifetime_count,
        }

    def build_report(self, node=None, levels=3):
        """Renders the tree [levels] deep."""
        if node == None: node = self

        if levels == 0: return

        key = node.key
        if not node.is_leaf():
            key = key + ":*"

        # Check to see if we print the key (only print the key and its parent).
        if levels == 1:

            report[key] = {
                'key': key,
                #'get': node.get,
                #'set': node.set,
                'leaf_count': node.leaf_count,
                #'hitrate': self.get_hitrate(node),
                'size': self.get_size(node),
                #'lifetime': self.get_lifetime(node)
            }
        
        if node.children is not None:
            for child in node.children:
                self.build_report(node=child, levels=levels - 1)
    
    def get_size(self, node):
        """Calculate the average size and convert it from Bytes to KB and round the result."""
        if node == None: node = self

        size = round(float(node.size) / float(1024), 2)

        #if size <= 0: 
        #    print node.key, node.size
        #    return '0'
        return size

    '''
    def get_hitrate(self, node):
        """Calculate the hitrate for the current node."""
        if node == None: node = self

        try:
            hitrate = 0
            gets = float(node.get)
            sets = float(node.set)
        except AttributeError:
            return 0

        if gets + sets > 0:
            hitrate = (gets / (gets + sets)) * 100

        return str(int(hitrate))

    def get_lifetime(self, node):
        """Proper format for the lifetime"""
        if node == None: node = self

        try:
            if node.lifetime_count == 0: return 'n/a'
        except AttributeError:
            return 'n/a'

        avg_lifetime = float(node.lifetime) / float(node.lifetime_count)

        lifetime = round(float(avg_lifetime), 2)
        if lifetime <= 0: return 'n/a'
        return lifetime
    '''

def print_report_header():
    print
    print '{:<90}'.format('Key'),
    print '{:<10}'.format('Nr. keys'),
    #print '{:<10}'.format('GET'),
    #print '{:<10}'.format('SET'),
    #print '{:<15}'.format('Hit Rate (%)'),
    print '{:<15}'.format('Size (KB)')
    #print '{:<20}'.format('Lifetime (seconds)')
    print '{:<170}'.format('-' * 170)


def redis_keys(keys):
    """Returns all the keys from the Redis server in the global connection pool."""
    r = redis.Redis(connection_pool=pool)
    return r.keys('*')
    
def redis_hgetall(keys):
    """Returns all the keys and their values from the Redis server in the global connection pool."""
    r = redis.Redis(connection_pool=pool)
    return "{}: {}".format(r.type(keys), keys)
    #return r.hgetall(keys)

def redis_get_size(key):
    r = redis.Redis(connection_pool=pool)
    key_type = r.type(key)

    object_size = 0

    if key_type == "hash":
        data = r.hgetall(key)

        for i, k in data.items():
            object_size += len(k)
    elif key_type == "set":
        data = r.smembers(key)

        for k in data:
            object_size += len(k)

    elif key_type == "string":
        data = r.get(key)
        object_size += len(data)

    return object_size

def save_object(obj, filename):
    """Saves an object to a file in a binary form to act as a caching mechanism."""
    with open(filename, 'wb') as o:
        pickle.dump(obj, o, pickle.HIGHEST_PROTOCOL)

def load_object(filename):
    """Loads an object from file."""
    with open(filename, 'rb') as i:
        return pickle.load(i)

if __name__ == '__main__':
    
    parser = ArgumentParser(description='Generates a memory utilization report from the Redis keys', formatter_class=RawTextHelpFormatter)
    parser.add_argument('--name', help='The name of this report (e.g. --name clientname). This is going to be stored locally so that future reports take less time.', required=True)
    parser.add_argument('--regenerate', action='store_true', help='Regenerate the report.', required=False)
    parser.add_argument('--level', help='How many levels deep the report should render.', required=False)
    parser.add_argument('--prefix', help='Filter by prefix.', required=False)
    
    args = vars(parser.parse_args())

    # The report object will be stored locally.
    if args['name']:
        filename = '/data/' + args['name'] + '.pkl'

    # Filter the report by prefix.
    prefix_filter = None
    if args['prefix']:
        prefix_filter = args['prefix']
        # Remove the wildcard in case we detect it.
        if prefix_filter.endswith('*'):
            prefix_filter = prefix_filter[:-1]
            
    # How deep do we want to go.
    levels = 3
    # The argument takes priority.
    if args['level']:
        levels = int(args['level'])
    elif prefix_filter is not None:
        # Try to automatically determine this based on prefix (if we have any).
        levels = len(prefix_filter.split(':')) + 1

    # Global connection pool to the local Redis.
    pool = redis.ConnectionPool(host='redis_monitor_db', port=6379, db=0)

    root = None

    # Flush the local data to regenerate the report.
    if args['regenerate']:
        if os.path.exists(filename): 
            os.remove(filename)

    # Attempts to load from cache.
    if os.path.exists(filename):
        root = load_object(filename)
        
    if not root:
        keys = redis_keys('*')

        root = MemoryReportNode('ROOT')
        root.build_tree(keys)

        # Show more feedback. Populating takes a few extra seconds.
        root.progress(100, 100, suffix='Almost there ...')
        root.populate()

        # Build the cache.
        save_object(root, filename)
    
    # Global variable which will be populated for sorting purposes.
    report = defaultdict(dict)
    root.build_report(levels=levels)
    report_sorted = sorted(report.items(), key=lambda item: int(item[1]['leaf_count']), reverse=True)

    print_report_header()

    for i, line in report_sorted:

        # We have a prefix filter.
        if prefix_filter is not None:
            line_ = line['key']
            if not line_.startswith(prefix_filter): continue

        if len(line['key']) > 80:
            line['key'] = line['key'][:80] + '...'

        print "{:<90}".format(line['key']),
        print "{:<10}".format(line['leaf_count']),
        #print "{:<10}".format(line['get']),
        #print "{:<10}".format(line['set']),
        #print "{:<15}".format(line['hitrate']),
        print "{:<15}".format(line['size'])
        #print "{:<20}".format(line['lifetime'])
 
    
        