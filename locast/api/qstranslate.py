from django.db.models import Q

from django.contrib.gis.geos import Point, Polygon
from django.contrib.gis.measure import D

from locast.api import strtodate
from locast.api.exceptions import InvalidParameterException

# TODO: * multiple ORDER BY support
#       * OR support?
#       * Make ruleset dicts into named tuples to be consistent with django

# example_ruleset = {
#    'author'        :    { 'type' : 'string', 'alias' : 'author__username' },
#    'title'         :    { 'type' : 'string' },
#    'description'   :    { 'type' : 'string' },
#    'created'       :    { 'type' : 'datetime' },
#    'modified'      :    { 'type' : 'datetime' },
#    'within'        :    { 'type' : 'geo_polygon', 'alias' : 'location__within' }
#}

# This takes a query string (in dict form) from an HTTP GET or POST and converts it 
# into a Django QuerySet to be used to filter objects. It uses a ruleset dictionary
# See above for an example
#
# i.e. ?author=username&date__lte=20091002 will result in 
# models.objects.filter(Q(author=username) & Q(date__lte = 20091002))

# Available types: string, int, list, geo_distance, geo_polygon,

class QueryTranslator:

    def __init__(self, ctype, ruleset, base_query = None, request = None):
        '''
        Create a new QueryTranslator

        Arguments:

            ctype
                The class of the object to query

            ruleset
                A rulset dictionary defining which parameters are
                queryable and what type they are. See above.

            base_query
                A Q object that is a query to seed the translator with.
                It will be run before anything passed in through a 
                query string.
        '''

        self.ctype = ctype
        self.ruleset = ruleset
        self.base_query = base_query
        self.request = request

    def filter(self, qdict):
        '''
        Run the filter based on a query dictionary passed in (request.GET or request.POST)

        Arguments:
            
            qdict
                The query dictionary (a la django request.GET or request.POST)
        '''

        q = Q()
        # Create a copy so qdict is mutable, and so it doesn't destroy it if it is already mutable
        qdict = qdict.copy()

        special_params = self.__extract_special_params(qdict, ['orderby','page','pagesize'])

        # Pagesize can just be used as a limiter to the number of objects to return.
        # Page should just default to 1
        if ('pagesize' in special_params) and (not 'page' in special_params):
            special_params['page'] = '1'

        try:
            self.__sanitize(qdict)
        except ValueError, e:
            raise InvalidParameterException(e.message)

        # Used to keep track of the values that are lists
        # these are taken into account afterwards
        lists = []
        
        for raw_field, value in qdict.items():

            # Deal with a list of items.
            # if len(value) > 1:
            f, m = self.__get_field(raw_field)
            type = self.ruleset[f]['type']
            if type == 'list':
                lists.append({raw_field:value})

            # A single item
            else:
                q = q & self.__get_query_obj(raw_field,value[0], type)

        if self.base_query: q = q & self.base_query

        objs = self.ctype.objects.filter(q)

        # Unfortunately, in order to AND together things like tags,
        # we have to chain filters after the QuerySet.
        #
        # Q(tags=tag1) & Q(tags=tag2) does not work.
        # self.ctype.objects.filter(tags=tag1).filter(tags=tag2)... does work

        if len(lists) > 0:
            for list in lists:

                # list is actually a dictionary. The key is the field
                # name, the value is the actual list.
                field = list.keys()[0]
                for list_item in list[field]:

                    # list is a list of strings
                    objs = objs.filter(self.__get_query_obj(field,list_item,'string'))

        if 'orderby' in special_params:
            orderby = special_params['orderby']
            desc = False
            if orderby[0] == '-': 
                orderby = orderby[1:]
                desc = True
            
            if orderby in self.ruleset:
                if 'alias' in self.ruleset[orderby]:
                    orderby = self.ruleset[orderby]['alias']

                if desc: orderby = '-' + orderby
                objs = objs.order_by(orderby)
            else:
                raise InvalidParameterException('Invalid orderby field: ' + orderby)

        objs = objs.distinct()

        return objs

    def __get_query_obj(self, field, value, type):
        '''
        Return a QuerySet object given a specific field and value
        '''

        field, modifier = self.__get_field(field)

        # Deal with alias
        if 'alias' in self.ruleset[field]:
            alias = self.ruleset[field]['alias']
            new_field = field.replace(field, alias, 1)
            field = new_field
            
        # Convert from unicode... need to add unicode support
        field = str(field)
        if len(modifier) != 0:
            field = field + '__' + str(modifier)

        # Deal with negation
        if type == 'string':
            if len(value) > 1 and value[0] == '~':
                value = value[1:]
                return ~Q(**{field:value})

        return Q(**{field:value})

    def __get_field(self, field):
        '''
        Takes a field from the query string, and splits out the field name
        and the modifier (i.e. author__contains returns author, contains)
        '''

        modifier = ''
        if field.find('__') != -1:
            field, modifier = field.split('__', 1)

        return field, modifier

    def __sanitize(self, qdict): 
        '''
        Convert the values into python types, sanitize them using the rule set.
        All values lists
        '''

        for k, v in qdict.items():

            field, modifier = self.__get_field(k)

            if field[0] == '_':
                del qdict[k]
            else:
                if not field in self.ruleset:
                    raise InvalidParameterException('Parameter not recognized: ' + field)

                # CHECK THE TYPE
                type = self.ruleset[field]['type']

                if type == 'string':
                    qdict[k] = [str(v)]

                elif type == 'int':
                    qdict[k] = [int(v)]

                elif type == 'bool':
                    qdict[k] = [(v.lower() == "true")]

                elif type == 'list':
                    list = v.split(',')
                    qdict[k] = list

                elif type == 'datetime':
                    qdict[k] = [strtodate(v)]

                elif type=='geo_distance':
                    # The value should be a tuple like this: (point, distance)
                    # where point is a Point object and distance a Distance object

                    dist = v.split(',')
                    pnt = Point(float(dist[0]), float(dist[1]))
                    # TODO: make the measurement type specifiable i.e. 30mi, 20km
                    #       right now it defaults to meters.
                    dist = D(m=dist[2])
                    qdict[k] = [(pnt, dist)]

                elif type=='geo_polygon':
                    pnts = v.split(',')
                    bbox = (float(pnts[0]), float(pnts[1]), 
                            float(pnts[2]), float(pnts[3]))
                    poly = Polygon.from_bbox(bbox)
                    # TODO: 4326 - this should be a setting?
                    poly.set_srid(4326)

                    qdict[k] = [poly]

                else:
                    qdict[k] = [str(v)]

    def __extract_special_params(self, qdict, params):
        '''
        Takes any params specified in params and removes them from the
        dict, and returns them as a separate dict
        '''
        special_params = {}

        for p in params:
            if p in qdict:
                if len(qdict[p]) > 0:
                    special_params[p] = qdict[p]
                del qdict[p]

        return special_params
