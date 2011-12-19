from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D

class TagRecommender:
    '''
    Recommends tags of a content model based on location
    ''' 

    def __init__(self, tag_model, content_model):
        '''
        Creates a new Tagrecommender.

        Arguments:
            
            tag_model
                Model class of tag to use

            content_model
                Model class of content to use
        '''

        self.tag_model = tag_model
        self.content_model = content_model
    
    def get_tags(self, location, num_tags=10, max_dist=4000, max_weight=4.0, min_weight=1.0, include_system=False):
        '''
        Returns an ordered list of tags based on a location, with the higher
        tags being more geographically relevant. The algorithm works as follows

        All tags within the radius of max_dist are considered. Each tag is given
        a weight based on location, which is determined linearly by the distance
        from the center, i.e. a tag directly on the given location would be given
        the maximum weight, while a tag directly on the perimiter of the circle
        would be given the minimum.

        All of the weights for a single semantic tag are aggregated into a final
        score, which is then used to order the tags returned.

        Arguments:
            
            location
                A tuple formatted as follows (lon, lat)

            num_tags
                Number of tags to return

            max_dist
                The maximum distance within which to consider tags

            max_weight
                The maximum float weight to assign tags closest to the center

            min_weight
                The float to assign tags furthest from the center, within
                the max_dist

            include_system
                Wether or not to include system tags
        '''

        center = Point(location[0], location[1])

        # max_dist is now a distance object
        max_dist = D(m=max_dist)

        # Get all contents within max_dist radius, and get them back in 'distance' format
        contents = self.content_model.objects.filter(location__distance_lte=(center,max_dist)).distance(center)

        distances = {}
        weights = []

        # max_dist is now a float of meters
        max_dist = max_dist.m

        weighted_tags = {}

        for content in contents:

            # distance is appended to content by the distance() queryset method
            dist = content.distance.m
            
            # Get the weight for all tags for this content
            # Weight between 1-4 where 1 is maximum distance and 4 is 0 distance
            weight = (((max_dist - dist) / max_dist) * (max_weight - min_weight)) + min_weight

            if include_system:
                tagqueryset = content.tags.all()
            else:
                tagqueryset = content.tags.filter(system_tag=False)

            for tagobj in tagqueryset:
                tag = tagobj.name
                if tag in weighted_tags:
                    weighted_tags[tag] += weight
                else:
                    weighted_tags[tag] = weight

        # Sorting dicts by value: http://www.python.org/dev/peps/pep-0265/
        recommended_tags = sorted(weighted_tags, key=weighted_tags.__getitem__, reverse=True)[:num_tags]
        
        return recommended_tags

