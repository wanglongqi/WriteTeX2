#!/usr/bin/env python
# -*- coding:utf-8
"""
writetex2.py
An Latex equation editor for Inkscape.

:Author: WANG Longqi <iqgnol@gmail.com>
:Date: 2017-04-01
:Version: v2.0.0

This file is a part of WriteTeX2 extension for Inkscape. For more information,
please refer to http://wanglongqi.github.io/WriteTeX.
"""

import inkex
import os
import tempfile
import sys
import copy
WriteTexNS = u'http://wanglongqi.github.io/WriteTeX'
# from textext
SVG_NS = u"http://www.w3.org/2000/svg"
XLINK_NS = u"http://www.w3.org/1999/xlink"


class WriteTex(inkex.Effect):

    def __init__(self):
        inkex.Effect.__init__(self)
        self.OptionParser.add_option("-p", "--preamble",
                                     action="store", type="string",
                                     dest="preamble", default="",
                                     help="Preamble File")
        self.OptionParser.add_option("--read-as-line",
                                     action="store", type="string",
                                     dest="preline", default="",
                                     help="Read preamble as string")
        self.OptionParser.add_option("-s", "--scale",
                                     action="store", type="string",
                                     dest="scale", default="",
                                     help="Scale Factor")
        self.OptionParser.add_option("-i", "--inputfile",
                                     action="store", type="string",
                                     dest="inputfile", default="",
                                     help="Read From File")
        self.OptionParser.add_option("-c", "--pdftosvg",
                                     action="store", type="string",
                                     dest="pdftosvg", default="",
                                     help="PDFtoSVG Converter")
        self.OptionParser.add_option("-k", "--keep",
                                     action="store", type="string",
                                     dest="keep", default="",
                                     help="Keep the object")
        self.OptionParser.add_option("-l", "--latexcmd",
                                     action="store", type="string",
                                     dest="latexcmd", default="xelatex",
                                     help="Latex command used to compile")

    def effect(self):
        self.zoom = float(self.document.xpath(
            '//sodipodi:namedview/@inkscape:zoom', namespaces=inkex.NSS)[0])
        self.width = 1/self.zoom * \
            float(self.document.xpath(
                '//sodipodi:namedview/@inkscape:window-width', namespaces=inkex.NSS)[0])
        self.height = 1/self.zoom * \
            float(self.document.xpath(
                '//sodipodi:namedview/@inkscape:window-height', namespaces=inkex.NSS)[0])
        self.width = self.unittouu(str(self.width)+'px')
        self.height = self.unittouu(str(self.height)+'px')

        self.options.scale = float(self.options.scale)
        if len(self.selected) == 0:
            inkex.errormsg("Select some text before click Apply.")
        for i in self.options.ids:
            node = self.selected[i]
            if node.tag != '{%s}g' % SVG_NS:
                self.text = "".join(node.itertext())
            if '{%s}text' % WriteTexNS in node.attrib:
                doc = inkex.etree.fromstring(
                    '<text x="%g" y="%g">%s</text>' % (
                        self.view_center[0]-self.width/6,
                        self.view_center[1]-self.height/6,
                        node.attrib.get(
                            '{%s}text' % WriteTexNS, '').decode('string-escape')))
                p = node.getparent()
                if self.options.keep == "false":
                    p.remove(node)
                p.append(doc)
                return

            tmp_dir = tempfile.mkdtemp("", "writetex-")
            tex_file = os.path.join(tmp_dir, "writetex.tex")
            svg_file = os.path.join(tmp_dir, "writetex.svg")
            pdf_file = os.path.join(tmp_dir, "writetex.pdf")
            log_file = os.path.join(tmp_dir, "writetex.log")
            out_file = os.path.join(tmp_dir, "writetex.out")
            err_file = os.path.join(tmp_dir, "writetex.err")
            aux_file = os.path.join(tmp_dir, "writetex.aux")
            crop_file = os.path.join(tmp_dir, "writetex-crop.pdf")

            if self.options.preline == "true":
                preamble = self.options.preamble
            else:
                if self.options.preamble == "":
                    preamble = ""
                else:
                    f = open(self.options.preamble)
                    preamble = f.read()
                    f.close()

            self.tex = r"""
            \documentclass[landscape,a3paper]{article}
            \usepackage{geometry}
            %s
            \pagestyle{empty}
            \begin{document}
            \noindent
            %s
            \end{document}
            """ % (preamble, self.text)

            tex = open(tex_file, 'w')
            tex.write(self.tex)
            tex.close()

            if self.options.latexcmd.lower() == "xelatex":
                os.popen('xelatex "-output-directory=%s" -interaction=nonstopmode -halt-on-error "%s" > "%s"'
                         % (tmp_dir, tex_file, out_file))
            elif self.options.latexcmd.lower() == "pdflatex":
                os.popen('pdflatex "-output-directory=%s" -interaction=nonstopmode -halt-on-error "%s" > "%s"'
                         % (tmp_dir, tex_file, out_file))
            else:
                # Setting `latexcmd` to following string produces the same result as xelatex condition:
                # 'xelatex "-output-directory={tmp_dir}" -interaction=nonstopmode -halt-on-error "{tex_file}" > "{out_file}"'
                os.popen(self.options.latexcmd.format(
                    tmp_dir=tmp_dir, tex_file=tex_file, out_file=out_file))

            try:
                os.popen('pdfcrop %s' % pdf_file)
                os.remove(pdf_file)
                os.rename(crop_file, pdf_file)
            except:
                pass

            if not os.path.exists(pdf_file):
                print >>sys.stderr, "Latex error: check your latex file and preamble."
                print >>sys.stderr, open(log_file).read()
            else:
                if self.options.pdftosvg == '1':
                    os.popen('pdf2svg %s %s' % (pdf_file, svg_file))
                    self.merge_pdf2svg_svg(svg_file)
                else:
                    os.popen('pstoedit -f plot-svg "%s" "%s"  -dt -ssp -psarg -r9600x9600 > "%s" 2> "%s"'
                             % (pdf_file, svg_file, out_file, err_file))
                    self.merge_pstoedit_svg(svg_file)

            os.remove(tex_file)
            os.remove(log_file)
            os.remove(out_file)
            if os.path.exists(err_file):
                os.remove(err_file)
            if os.path.exists(aux_file):
                os.remove(aux_file)
            if os.path.exists(svg_file):
                os.remove(svg_file)
            if os.path.exists(pdf_file):
                os.remove(pdf_file)
            os.rmdir(tmp_dir)

    def merge_pstoedit_svg(self, svg_file):
        def svg_to_group(self, svgin):
            innode = svgin.tag.rsplit('}', 1)[-1]
            # replace svg with group by select specific elements
            if innode == 'svg':
                svgout = inkex.etree.Element(inkex.addNS('g', 'WriteTexNS'))
            else:
                svgout = inkex.etree.Element(inkex.addNS(innode, 'WriteTexNS'))
                for att in svgin.attrib:
                    svgout.attrib[att] = svgin.attrib[att]

            for child in svgin.iterchildren():
                tag = child.tag.rsplit('}', 1)[-1]
                if tag in ['g', 'path', 'line']:
                    child = svg_to_group(self, child)
                    svgout.append(child)
            return svgout

        doc = inkex.etree.parse(svg_file)
        svg = doc.getroot()
        newnode = svg_to_group(self, svg)
        newnode.attrib['{%s}text' %
                       WriteTexNS] = self.text.encode('string-escape')
        node = self.selected[self.options.ids[0]]
        try:
            if 'transform' in node.attrib:
                newnode.attrib['transform'] = node.attrib['transform']
            else:
                newnode.attrib['transform'] = 'matrix(%f,0,0,%f,%f,%f)' % (
                    800*self.options.scale, 800*self.options.scale,
                    self.view_center[0]-self.width/6,
                    self.view_center[1]-self.height/6)
            newnode.attrib['style'] = node.attrib['style']
        except:
            pass

        p = node.getparent()
        if self.options.keep == "false":
            p.remove(node)
        p.append(newnode)

    def merge_pdf2svg_svg(self, svg_file):
        def svg_to_group(self, svgin):
            target = {}
            for node in svgin.xpath('//*[@id]'):
                target['#'+node.attrib['id']] = node

            for node in svgin.xpath('//*'):
                if ('{%s}href' % XLINK_NS) in node.attrib:
                    href = node.attrib['{%s}href' % XLINK_NS]
                    p = node.getparent()
                    p.remove(node)
                    trans = 'translate(%s,%s)' % (
                        node.attrib['x'], node.attrib['y'])
                    for i in target[href].iterchildren():
                        i.attrib['transform'] = trans
                        p.append(copy.copy(i))

            svgout = inkex.etree.Element(inkex.addNS('g', 'WriteTexNS'))
            for node in svgin:
                if node is svgout:
                    continue
                if node.tag == '{%s}defs' % SVG_NS:
                    continue
                svgout.append(node)
            return svgout

        doc = inkex.etree.parse(svg_file)
        svg = doc.getroot()
        newnode = svg_to_group(self, svg)
        newnode.attrib['{%s}text' %
                       WriteTexNS] = self.text.encode('string-escape')

        node = self.selected[self.options.ids[0]]

        try:
            if 'transform' in node.attrib:
                newnode.attrib['transform'] = node.attrib['transform']
            else:
                newnode.attrib['transform'] = 'matrix(%f,0,0,%f,%f,%f)' % (
                    self.options.scale, self.options.scale,
                    self.view_center[0]-self.width/6,
                    self.view_center[1]-self.height/6)
            newnode.attrib['style'] = node.attrib['style']
        except:
            pass

        p = node.getparent()
        if self.options.keep == "false":
            p.remove(node)
        p.append(newnode)


if __name__ == '__main__':
    e = WriteTex()
    e.affect()
