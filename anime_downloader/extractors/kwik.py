import logging
import re
from anime_downloader.extractors.base_extractor import BaseExtractor
from anime_downloader.sites import helpers
from anime_downloader.util import base36encode

logger = logging.getLogger(__name__)


class Kwik(BaseExtractor):
    '''Extracts video url from kwik pages, Kwik has some `security`
       which allows to access kwik pages when only refered by something
       and the kwik video stream when refered through the corresponding
       kwik video page.
    '''

    def _get_data(self):

        # Need a better javascript deobfuscation api/python, so someone smarter
        # than me can work on that for now I will add the pattern I observed

        # Kwik has added dirty javascript packing, a general solution will need
        # a headless browser (to render the js) which is too big a dependency.
        # For now, manually unpacking to extract url, token
        # Will need to be changed when Kwik changes their js packing mechanism

        def get_source_parts(page_text):
            
            def unpack_javascript(p, a, c, k, _e, d):

                def e(c):
                    c2 = c % a
                    return (
                        ("" if c < a else e(c//a)) +
                        (chr(c2 + 29) if c2 > 35 else base36encode(c2).lower())
                    )
                d.update((e(i), k[i] or e(i)) for i in range(c))

                clear_js = re.sub("\\b\\w+\\b", lambda i: d[i.group()], p)

                var_name = re.search(r'\b(\w+)\.split\(""\)', clear_js).group(1)
                token    = re.search(f'var {var_name}="(\\w+)"', clear_js).group(1)[::-1]
                post_url = re.search(r'<form action="(.*)"method="POST">', clear_js).group(1)

                return post_url, token

            # Extract Arguments of the packed javascript function
            m = re.search(
                r'<script>\s*eval\(function\(p,a,c,k,e,d\).*}(\(.*\))\)\s*</script>', page_text)
            return eval('unpack_javascript' + m.group(1))        

        # Kwik servers don't have direct link access you need to be referred
        # from somewhere, I will just use the url itself.

        download_url = self.url.replace('kwik.cx/e/', 'kwik.cx/f/')

        kwik_text = helpers.get(download_url, referer=download_url).text
        post_url, token = get_source_parts(kwik_text)

        stream_url = helpers.post(post_url,
                                  referer=download_url,
                                  data={'_token': token},
                                  allow_redirects=False).headers['Location']

        title = stream_url.rsplit('/', 1)[-1].rsplit('.', 1)[0]

        logger.debug('Stream URL: %s' % stream_url)
        return {
            'stream_url': stream_url,
            'meta': {
                'title': title,
                'thumbnail': ''
            },
            'referer': None
        }
