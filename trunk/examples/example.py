#!/usr/bin/python
import sys,math

sys.path.append("../src")
import smart_gnuplotter
reload(smart_gnuplotter)

g = smart_gnuplotter.smart_gnuplotter()
# g.default_terminal = 'epslatex color size 10cm,4cm font "" 10'
# g.default_pause = 1


if 1:
    g.set_graph_attrs()
    # g.add_plots("sin(x)")
    g.add_plots("cos(x)", plot_with="histogram")
    g.show_graphs()

# simplest example
if 1:
    g.graphs("x * x",
             output="graphs/xx")

# 3 plots in a graph
if 1:
    g.graphs("%(a)s * x", 
             output="graphs/ax",
             a=[1,2,3])

# 3x3x3 plots in a graph
if 1:
    g.graphs("%(a)s * x * x + %(b)s * x + %(c)s", 
             output="graphs/a_xx_bx_c",
             a=[1,2,3], b=[4,5,6], c=[7,8,9])

# 3x3 plots in each of 3 graphs
if 1:
    g.graphs("%(a)s * x * x + %(b)s * x + %(c)s", 
             a=[1,2,3], b=[4,5,6], c=[7,8,9],
             output="graphs/%(a)s_xx_bx_c",
             graph_vars=["a"])

# 3x3 plots with attributes
if 1:
    g.graphs("%(a)s * x * x + %(b)s * x + %(c)s", 
             a=[1,2,3], b=[4,5,6], c=[7,8,9],
             output="graphs/%(a)s_xx_bx_c_with_attr",
             gpl_file="graphs/%(a)s_xx_bx_c_with_attr.gpl",
             graph_vars=["a"],
             graph_attr=r'''
set title "$%(a)sx^2+bx+c$"
''',
             plot_attr=r'''title "$%(a)sx^2+%(b)sx+%(c)s$"''')

if 1:
    g.graphs([("a",10), ("b",20), ("c", 30)], 
             output="graphs/symbolic_x",
             yrange="[0:]",
             boxwidth="0.9 relative", 
             plot_with="boxes fs pattern 1")

# python list
if 1:
    g.graphs([ (x,math.sqrt(x)) for x in range(10) ],
             output="graphs/sqrtx")

# python list, but x axis values are symbol
if 1:
    g.graphs([ ("one",  math.pow(1, 1.0/2)),
               ("two",  math.pow(2, 1.0/2)),
               ("three",math.pow(3, 1.0/2)),
               ("four", math.pow(4, 1.0/2)) ],
             output="graphs/one_two_three_four",
             boxwidth="0.9 relative",
             yrange="[0:3]",
             plot_with="boxes fs solid 0.25")

if 1:
    g.graphs(("example.sqlite", 
              r"""select a,b from t"""),
             output="graphs/select_example")

print "OK"



