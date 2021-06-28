#!/usr/bin/env python3

#=============================================================================
# Searches all HTML files specified on the command line for internal links that
# have problems, reporting them to standard output.
#=============================================================================

from argparse     import ArgumentParser
from fnmatch      import filter as fnfilter
from lxml         import etree
from os           import walk
from os.path      import dirname, exists, isabs, isdir, join, normpath, realpath
from urllib.parse import urlparse

# Directories are searched for files matching any of these patterns.
FILE_PATTERNS = ['*.htm', '*.HTM', '*.html', '*.HTML']

#-----------------------------------------------------------------------------
# Class used to process files to find broken links.
#-----------------------------------------------------------------------------

class FileProcessor(object):
    """Helper class that does the work of finding anchors and reporting broken
    links."""
    def __init__(self):
        # HTML parser used to process files.
        self._parser = etree.HTMLParser()
        # Set of anchors. Each item in the set is a string: "path:element".
        self._anchors = set()

    def ProcessPaths(self, paths):
        """Processes a list of file paths. Each file is first processed to find
        anchors in it, which are added to a set. Then each file is processed to
        search for links to internal targets that are not in the set of
        anchors. If any are found, a message is printed to standard output."""
        for path in paths:
            self._CollectAnchors(path)
        for path in paths:
            self._FindBrokenLinks(path)

    # -------------------------------------------------------------------------
    # Implementation.
    # -------------------------------------------------------------------------

    def _CollectAnchors(self, path):
        """Collects all anchors for the file with the given path, adding them
        to the _anchors set."""
        root = self._ParseFile(path)
        if not root is None:
            # Add the path itself as a target (with no named element).
            self._AddAnchor(path, '')
            # Add all anchor elements ("<a>") with a "name" attribute.
            for elt in root.findall('.//a[@name]'):
                self._AddAnchor(path, elt.attrib['name'])
            # Add all elements that have an "id" tag.
            for elt in root.findall('.//*[@id]'):
                self._AddAnchor(path, elt.attrib['id'])
        # Uncomment this to help debug:
        # self._PrintAnchors(path)

    def _FindBrokenLinks(self, path):
        """Looks at all internal links in the file with the given path,
        reporting any whose targets are not in the _anchors set."""
        root = self._ParseFile(path)
        if not root is None:
            # Examine all anchor elements with an "href" attribute.
            for elt in root.findall('.//a[@href]'):
                href = elt.attrib['href']
                # Look at only internal (relative) references.
                anchor = self._GetAnchor(path, href)
                if anchor and not anchor in self._anchors:
                    self._ReportBrokenLink(path, elt, href)

    def _ParseFile(self, path):
        """Parses the HTML file with the given path. If it works, this returns
        the root element of the resulting tree. Otherwise, it
        prints an error message and returns None."""
        try:
            tree = etree.parse(path, self._parser)
            return tree.getroot()
        except:
            print(f'*** Unable to parse HTML from "{path}"')
            return None

    def _AddAnchor(self, path, element_name):
        self._anchors.add(f'{path}:{element_name}')

    def _GetAnchor(self, path, href):
        """Returns an anchor in the correct form ("path:element") based on the
        given path and href contents. Returns an empty string if the href is an
        external reference or to an existing file or directory (with no element
        name)."""
        url = urlparse(href)
        if url.scheme:  # External link.
            return ''

        # If there is a path in the URL, use it. Deal properly with relative
        # paths.
        if url.path:
            ref_path = (url.path if isabs(url.path)
                        else realpath(normpath(join(dirname(path), url.path))))
        else:
            ref_path = path

        # If there is no fragment, make sure the path corresponds to a real
        # file or directory. If it is, return an empty string.
        if not url.fragment:
            if exists(ref_path):
                return ''

        # If there is a fragment and the path is a directory, add 'index.html'
        # so that the path is a real file.
        else:
            if isdir(ref_path):
                ref_path += '/index.html'

        return f'{ref_path}:{url.fragment}'

    def _ReportBrokenLink(self, path, elt, href):
        print(f'*** Line {elt.sourceline} in "{path}":')
        print(f'***     Broken link to "{href}"')

    def _PrintAnchors(self, path):
        """Debugging aid."""
        print(f'==== ANCHORS in {path}:')
        for anchor in sorted(self._anchors):
            print(f'====     {anchor}')

#-----------------------------------------------------------------------------
# Command-line argument processing.
#-----------------------------------------------------------------------------

def ProcessArguments():
    description = (
        """Searches HTML files for bad internal links, reporting problems to
        standard output.""")
    parser = ArgumentParser(description=description)
    parser.add_argument(
        'inputs', nargs='*',
        help="""HTML files and directories containing HTML files to check. If
        none are specified, uses the current directory. Directories are
        searched for files with extensions "htm", "HTM", "html", or "HTML".""")
    return parser

#-----------------------------------------------------------------------------
# Given a list of paths to input files and directories, this returns a sorted
# list of paths to HTML files to process.
# -----------------------------------------------------------------------------

def GetFilePaths(file_and_dir_paths):
    def _GetPathsForDir(directory):
        paths = []
        for root, dirnames, filenames in walk(directory):
            fns = []
            for pattern in FILE_PATTERNS:
                fns += fnfilter(filenames, pattern)
            paths += [realpath(join(root, fn)) for fn in fns]
        return paths;
    all_paths = []
    for path in file_and_dir_paths:
        if isdir(path):
            all_paths += _GetPathsForDir(path)
        else:
            all_paths.append(realpath(path))
    return sorted(all_paths)

# -----------------------------------------------------------------------------
# Mainline.
# -----------------------------------------------------------------------------

def main():
    parser = ProcessArguments()
    args = parser.parse_args()

    paths = GetFilePaths(args.inputs or '.')

    processor = FileProcessor()
    processor.ProcessPaths(paths)

if __name__ == '__main__':
    main()
