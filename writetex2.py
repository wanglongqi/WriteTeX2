#!/usr/bin/env python
# -*- coding:utf-8
"""
writetex2.py
An Latex equation editor for Inkscape.

:Author: WANG Longqi <iqgnol@gmail.com>
:Date: 2019-04-19
:Version: v2.1.0

This file is a part of WriteTeX2 extension for Inkscape. For more information,
please refer to http://wanglongqi.github.io/WriteTeX.
"""
from __future__ import print_function
import inkex
import os
import tempfile
import sys
import copy
import subprocess
import re
# from distutils import spawn
WriteTexNS = u'http://wanglongqi.github.io/WriteTeX'
# from textext
SVG_NS = u"http://www.w3.org/2000/svg"
XLINK_NS = u"http://www.w3.org/1999/xlink"


class WriteTex(inkex.Effect):

    def __init__(self):
        inkex.Effect.__init__(self)
        self.OptionParser.add_option("-f", "--formula",
                                     action="store", type="string",
                                     dest="formula", default="",
                                     help="LaTeX formula")
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
        self.OptionParser.add_option("--action", action="store",
                                     type="string", dest="action",
                                     default=None, help="")
        self.OptionParser.add_option("-k", "--keep",
                                     action="store", type="string",
                                     dest="keep", default="",
                                     help="Keep the object")
        self.OptionParser.add_option("-l", "--latexcmd",
                                     action="store", type="string",
                                     dest="latexcmd", default="xelatex",
                                     help="Latex command used to compile")

    def effect(self):
        self.options.scale = float(self.options.scale)
        if len(self.selected) == 0:
            inkex.errormsg("Select some text before click Apply.")
        for i in self.options.ids:
            node = self.selected[i]
            if node.tag != '{%s}g' % SVG_NS:
                self.text = "".join(node.itertext())
            if '{%s}text' % WriteTexNS in node.attrib:
                doc = inkex.etree.fromstring(
                    '<text x="%g" y="%g" xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd">%s</text>' % (
                        self.view_center[0],
                        self.view_center[1],
                        self.break_line(node.attrib.get(
                            '{%s}text' % WriteTexNS, '').decode('string-escape'))))
                p = node.getparent()
                if 'transform' in node.attrib:
                    doc.attrib['eqtransform'] = node.attrib['transform']
                if 'style' in node.attrib:
                    doc.attrib['eqstyle'] = node.attrib['style']
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
                subprocess.call('xelatex "-output-directory=%s" -interaction=nonstopmode -halt-on-error "%s" > "%s"'
                                % (tmp_dir, tex_file, out_file), shell=True)
            elif self.options.latexcmd.lower() == "pdflatex":
                subprocess.call('pdflatex "-output-directory=%s" -interaction=nonstopmode -halt-on-error "%s" > "%s"'
                                % (tmp_dir, tex_file, out_file), shell=True)
            else:
                # Setting `latexcmd` to following string produces the same result as xelatex condition:
                # 'xelatex "-output-directory={tmp_dir}" -interaction=nonstopmode -halt-on-error "{tex_file}" > "{out_file}"'
                subprocess.call(self.options.latexcmd.format(
                    tmp_dir=tmp_dir, tex_file=tex_file, out_file=out_file), shell=True)

            if not os.path.exists(pdf_file):
                print("Latex error: check your latex file and preamble.",
                      file=sys.stderr)
                print(open(log_file).read(), file=sys.stderr)
                return
            else:
                if self.options.pdftosvg == '1':
                    subprocess.call('pdf2svg %s %s' %
                                    (pdf_file, svg_file), shell=True)
                    self.merge_pdf2svg_svg(svg_file)
                else:
                    subprocess.call('pstoedit -f plot-svg "%s" "%s"  -dt -ssp -psarg -r9600x9600 > "%s" 2> "%s"'
                                    % (pdf_file, svg_file, out_file, err_file), shell=True)
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

            # TODO: add crop range code here.

            return svgout

        doc = inkex.etree.parse(svg_file)
        svg = doc.getroot()
        newnode = svg_to_group(self, svg)
        newnode.attrib['{%s}text' %
                       WriteTexNS] = self.text.encode('string-escape')
        node = self.selected[self.options.ids[0]]
        try:
            if 'eqtransform' in node.attrib:
                newnode.attrib['transform'] = node.attrib['eqtransform']
            else:
                newnode.attrib['transform'] = 'matrix(%f,0,0,%f,%f,%f)' % (
                    800 * self.options.scale, 800 * self.options.scale,
                    self.view_center[0] - self.width / 6,
                    self.view_center[1] - self.height / 6)
            if 'eqstyle' in node.attrib:
                newnode.attrib['style'] = node.attrib['eqstyle']
        except Exception as e:
            print(e, file=sys.stderr)

        p = node.getparent()
        if self.options.keep == "false":
            p.remove(node)
        p.append(newnode)

    def merge_pdf2svg_svg(self, svg_file):
        # This is the smallest point coordinates assumed
        MAX_XY = [-10000000, -10000000]

        def svg_to_group(self, svgin):
            target = {}
            for node in svgin.xpath('//*[@id]'):
                target['#' + node.attrib['id']] = node

            for node in svgin.xpath('//*'):
                if ('{%s}href' % XLINK_NS) in node.attrib:
                    href = node.attrib['{%s}href' % XLINK_NS]
                    p = node.getparent()
                    p.remove(node)
                    trans = 'translate(%s,%s)' % (
                        node.attrib['x'], node.attrib['y'])
                    for i in target[href].iterchildren():
                        i.attrib['transform'] = trans
                        x, y = self.parse_transform(trans)
                        if x > MAX_XY[0]:
                            MAX_XY[0] = x
                        if y > MAX_XY[1]:
                            MAX_XY[1] = y
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
            if 'eqtransform' in node.attrib:
                newnode.attrib['transform'] = node.attrib['eqtransform']
            else:
                newnode.attrib['transform'] = 'matrix(%f,0,0,%f,%f,%f)' % (
                    self.options.scale, self.options.scale,
                    self.view_center[0] - MAX_XY[0] * self.options.scale,
                    self.view_center[1] - MAX_XY[1] * self.options.scale)
            if 'eqstyle' in node.attrib:
                newnode.attrib['style'] = node.attrib['eqstyle']
        except Exception as e:
            print(e, file=sys.stderr)

        p = node.getparent()
        if self.options.keep == "false":
            p.remove(node)
        p.append(newnode)

    @staticmethod
    def parse_transform(transf):
        if transf == "" or transf is None:
            return(0, 0)
        stransf = transf.strip()
        result = re.match(
            r"(translate|scale|rotate|skewX|skewY|matrix)\s*\(([^)]*)\)\s*,?",
            stransf)
        if result.group(1) == "translate":
            args = result.group(2).replace(',', ' ').split()
            dx = float(args[0])
            if len(args) == 1:
                dy = 0.0
            else:
                dy = float(args[1])
            return (dx, dy)
        else:
            return (0, 0)

    MAX_COL = 80

    @staticmethod
    def break_line(string):
        if len(string) < WriteTex.MAX_COL:
            return string
        parts = string.split('\\')
        out = []
        line = parts[0]
        for part in parts[1:]:
            if len(line) < WriteTex.MAX_COL:
                line += '\\' + part
            else:
                out.append(line)
                line = '\\' + part
        if line:
            out.append(line)
        if len(out) == 1:
            return string

        if ''.join(out) == string:
            return ' '.join(['<tspan sodipodi:role="line" style="line-height:2em;">%s</tspan>' % l.strip() for l in out])
        else:
            return string


if __name__ == '__main__':
    e = WriteTex()
    e.affect()
