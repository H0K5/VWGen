from VWGen.core.attack.attack import Attack
import os
import re
import sys
import json
import random

try:
    from lxml import etree
except ImportError:
    print("Failed to import ElementTree from any known place")
    sys.exit(0)

try:
    from bs4 import UnicodeDammit  # BeautifulSoup 4

    def decode_html(html_string):
        converted = UnicodeDammit(html_string)
        if not converted.unicode_markup:
            raise UnicodeDecodeError(
                "Failed to detect encoding, tried [%s]",
                ', '.join(converted.tried_encodings))
        return converted.unicode_markup
except ImportError:
    from BeautifulSoup import UnicodeDammit  # BeautifulSoup 3

    def decode_html(html_string):
        converted = UnicodeDammit(html_string, isHTML=True)
        if not converted.unicode:
            raise UnicodeDecodeError(
                "Failed to detect encoding, tried [%s]",
                ', '.join(converted.triedEncodings))
        return converted.unicode


class mod_lfi(Attack):
    """This class implements a Local File Inclusion vulnerabilities generator."""

    name = "lfi"

    payloads = []
    settings = {}
    highest = 2
    index = random.randint(0, highest)
    CONFIG_FILE = "lfiPayloads.txt"
    require = ["unfilter"]
    PRIORITY = 4

    def __init__(self, fp=None):
        Attack.__init__(self, fp)
        self.fd = open(os.path.join(self.CONFIG_DIR,
                                    self.name, self.CONFIG_FILE), "r+")
        self.payloads = json.load(self.fd)

    def findRequireFiles(self, backend, dbms):
        return self.payloads['preprocessing']['{0}'.format(backend)]

    def generateHandler(self, tree_node=None, o=None, elem=None):
        if elem['type'] != "attrval":
            o[int(elem['lineno']) - 1] = re.sub(r'(.*)<{0}>(.*)</{0}>(.*)'.format(elem['identifier']), lambda m: "{0}{1}{2}".format(m.group(
                1), self.payloads['payloads'][self.index]['vector'].replace('{0}', m.group(2)), m.group(3)), o[int(elem['lineno']) - 1], flags=re.IGNORECASE)
        else:
            o[int(elem['lineno']) - 1] = re.sub(r'(.*)#+<{0}>(.*)</{0}>(.*)'.format(elem['identifier']), lambda m: "{0}{1}{2}".format(m.group(
                1), self.payloads['payloads'][self.index]['vector'].replace('{0}', m.group(2)), m.group(3)), o[int(elem['lineno']) - 1], flags=re.IGNORECASE)

        if self.settings['key'] is not None:
            for index, _ in enumerate(self.settings['key']):
                if self.payloads['payloads'][self.index]['restrict']['include_value']:
                    for restrict in self.payloads['payloads'][self.index]['restrict']['include_value']:
                        if restrict.startswith("-"):
                            restrict = restrict[1:]
                            self.settings['value'][index] = self.settings['lficonfig'][
                                :self.settings['lficonfig'].index(restrict)]
                        else:
                            restrict = restrict[1:]
                            self.settings['value'][index] = "".join(
                                self.settings['lficonfig'], restrict)
                else:
                    self.settings['value'][
                        index] = self.settings['lficonfig']

    def doJob(self, http_res, backend, dbms, parent=None):
        """This method do a Job."""
        try:
            self.settings['lficonfig'] = self.findRequireFiles(backend, dbms)
            self.settings = self.generate_payloads(
                self.settings['html'], parent=parent)

        except:
            self.logR("ERROR!! You might forget to set Backend variable.")
            raise RuntimeError

        return self.settings

    def study(self, etree_node, entries=None, lines=None, parent=None):
        for identifier in ["inject"]:
            found_node = etree_node.xpath("//*[@*[re:test(., '{0}', 'i')] or @*[re:test(name(.), '{0}', 'i')] or re:test(local-name(),'{0}', 'i') or text()[re:test(., '{0}', 'i')]]".format(
                identifier), namespaces={'re': "http://exslt.org/regular-expressions"})
            if found_node is not None and len(found_node) != 0:
                for node in found_node:
                    if identifier in node.tag:
                        if self.verbose:
                            self.logY("Found in tag name {0}".format(node.tag))
                        d = {"type": "tag", "value": node.tag, "lineno": node.getparent().getprevious().text.strip() if node.getparent(
                        ).getprevious() is not None else node.getparent().getparent().getprevious().text.strip(), "identifier": identifier}
                        if d not in entries:
                            if self.verbose:
                                self.logY("\t{0}".format(d))
                            entries.append(d)
                    elif node.text is not None and identifier in node.text:
                        if self.verbose:
                            self.logY(
                                "Found in text, tag {0}".format(node.tag))
                        d = {"type": "text", "parent": node.tag, "lineno": node.getprevious().text.strip() if node.getprevious(
                        ) is not None else node.getparent().getprevious().text.strip(), "identifier": identifier}
                        if d not in entries:
                            if self.verbose:
                                self.logY("\t{0}".format(d))
                            entries.append(d)
                    for k, v in node.attrib.iteritems():
                        if identifier in v:
                            if self.verbose:
                                self.logY(
                                    "Found in attribute value {0} of tag {1}".format(k, node.tag))
                            d = {"type": "attrval", "name": k, "tag": node.tag, "lineno": node.getprevious(
                            ).text.strip(), "identifier": identifier}
                            if d not in entries:
                                if self.verbose:
                                    self.logY("\t{0}".format(d))
                                entries.append(d)
                        if identifier in k:
                            if self.verbose:
                                self.logY(
                                    "Found in attribute name {0} of tag {1}".format(k, node.tag))
                            d = {"type": "attrname", "name": k, "tag": node.tag, "lineno": node.getprevious(
                            ).text.strip(), "identifier": identifier}
                            if d not in entries:
                                if self.verbose:
                                    self.logY("\t{0}".format(d))
                                entries.append(d)
            found_node = etree_node.xpath("//comment()[re:test(., '{0}', 'i')]".format(
                identifier), namespaces={'re': "http://exslt.org/regular-expressions"})
            if found_node is not None and len(found_node) != 0:
                for node in found_node:
                    if self.verbose:
                        self.logY(
                            "Found in comment, content: \"{0}\"".format(node))
                    d = {"type": "comment", "lineno": (node.getparent().getprevious().text.strip()) if (
                        node.getprevious() is None) else (node.getprevious().text.strip()), "identifier": identifier}
                    if d not in entries:
                        if self.verbose:
                            self.logY("\t{0}".format(d))
                        entries.append(d)

    # Generate payloads based on what situations we met.
    def generate_payloads(self, html_code, parent=None):
        e = []
        o = []
        l = []

        for index, line in enumerate(html_code.splitlines(), 1):
            o.append(line)
            l.append("<!-- {0} -->{1}".format(index, line))

        tree = etree.HTML(decode_html("\n".join(l))).getroottree()
        self.study(tree, entries=e, lines=l, parent=parent)

        for elem in e:
            # <a href="inject_point"></a>
            if elem['type'] == "attrval":
                found_node = etree.HTML(l[int(elem['lineno']) - 1]).xpath("//*[@*[re:test(., '{0}', 'i')]]".format(
                    elem['identifier']), namespaces={'re': "http://exslt.org/regular-expressions"})
                if len(found_node) == 1:
                    self.generateHandler(tree_node=tree, o=o, elem=elem)
            # <a inject_point="test">
            elif elem['type'] == "attrname":
                found_node = etree.HTML(l[int(elem['lineno']) - 1]).xpath("//*[@*[re:test(name(.), '{0}', 'i')]]".format(
                    elem['identifier']), namespaces={'re': "http://exslt.org/regular-expressions"})
                if len(found_node) == 1:
                    self.generateHandler(tree_node=tree, o=o, elem=elem)
            # <inject_point name="test" />
            elif elem['type'] == "tag":
                found_node = etree.HTML(l[int(elem['lineno']) - 1]).xpath("//*[re:test(local-name(), '{0}', 'i')]".format(
                    elem['identifier']), namespaces={'re': "http://exslt.org/regular-expressions"})
                if len(found_node) == 1:
                    self.generateHandler(tree_node=tree, o=o, elem=elem)
            # <span>inject_point</span>
            elif elem['type'] == "text":
                found_node = etree.HTML(
                    l[int(elem['lineno']) - 1]).xpath("//*[text()]")
                if len(found_node) == 1:
                    self.generateHandler(tree_node=tree, o=o, elem=elem)
            # <!-- inject_point -->
            elif elem['type'] == "comment":
                try:
                    found_node = etree.HTML(
                        l[int(elem['lineno']) - 1]).xpath("//*[comment()]")
                except:
                    found_node = etree.HTML("{0}{1}{2}".format("<div>", l[int(elem['lineno']) - 1], "</div>")).xpath(
                        "//comment()[re:test(., '{0}', 'i')]".format(elem['identifier']), namespaces={'re': "http://exslt.org/regular-expressions"})
                if len(found_node) == 1:
                    self.generateHandler(tree_node=tree, o=o, elem=elem)

        self.settings['html'] = "\n".join(o)

        return self.settings

    def final(self):
        self.fp.write(os.path.join(self.fp.path, self.fp.target),
                      self.settings['html'], ext=None)
        lines = self.fp.readLines(os.path.join(
            self.CONFIG_DIR, 'php.ini.sample'))

        if self.payloads['payloads'][self.index]['restrict']['php.ini']:
            with open(os.path.join(self.fp.path, 'php.ini'), 'w') as f:
                for line in lines:
                    found = False
                    for key, value in self.payloads['payloads'][self.index]['restrict']['php.ini'].iteritems():
                        if re.match(r'{0}'.format('^' + key + '(\s*=\s*).*'), line) and not found:
                            found = True
                            f.write(re.sub(r'{0}'.format('^' + key + '(\s*=\s*).*'), lambda m: "{0}{1}{2}".format(
                                key, m.group(1), value), line, flags=re.IGNORECASE))
                    if not found:
                        f.write(line)

        if self.verbose:
            self.logY("Copy \"{0}\" to \"{1}\"".format(os.path.join(self.CONFIG_DIR, self.name, self.settings[
                      'lficonfig']), os.path.join(self.fp.path, self.settings['lficonfig'])))
        self.fp.copy(os.path.join(self.CONFIG_DIR, self.name, self.settings[
                     'lficonfig']), os.path.join(self.fp.path, self.settings['lficonfig']))
