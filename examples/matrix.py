#!/usr/bin/python

import sys

sys.path.append("../src")

import smart_gnuplotter
reload(smart_gnuplotter)

g = smart_gnuplotter.smart_gnuplotter()
# g.default_terminal = 'epslatex color size 10cm,5cm font "" 10'

db = "matrix.sqlite"

Ms    = g.do_sql(db, "select distinct M from a where M > 500", single_col=1)
archs = g.do_sql(db, "select distinct arch from a", single_col=1)
parallel_types = g.do_sql(db, "select distinct type from a where ppn > 1", 
                          single_col=1)

if 0:
    query = r'''select type,avg(gflops_per_sec) from a 
where M = %(M)s and ppn = 1 and arch = "%(arch)s" 
group by type'''
    g.graphs((db, query), 
             output="graphs/serial_%(arch)s_%(M)s.tex",
             plot_title="",
             plot_with="boxes fs pattern 1",
             boxwidth="0.9 relative",
             graph_title="%(arch)s M=%(M)s",
             yrange="[0:]",
             xlabel="Program",
             ylabel="Performance (GFLOPS)",
             M=Ms, arch=archs, graph_vars=[ "arch", "M" ])
    
if 0:
    query = r'''select ppn,avg(gflops_per_sec) from a 
where type="%(typ)s" and M=%(M)s and arch="%(arch)s" 
group by ppn'''
    g.graphs((db, query), 
             output="graphs/gflops_%(arch)s_%(M)s.tex",
             plot_title="%(typ)s",
             plot_with="linespoints",
             graph_title="%(arch)s M=%(M)s",
             xrange="[0:]",
             yrange="[0:]",
             xlabel="cores",
             ylabel="Performance (GFLOPS)",
             typ=parallel_types, M=Ms, arch=archs, graph_vars=[ "arch", "M" ])
    
if 1:
    init = r'''
create temp table serial as 
select arch,M,avg(gflops_per_sec) serial_gflops_per_sec 
from a where type = "serial" 
group by arch,M;

create temp table b as select * from serial natural join a;
'''
    query = r'''select ppn,avg(gflops_per_sec / serial_gflops_per_sec) from b
where type="%(typ)s" and M=%(M)s and arch="%(arch)s" group by ppn'''
    g.graphs((db, query, init), 
             output="graphs/speedup_%(arch)s_%(M)s.tex",
             plot_title="%(typ)s",
             plot_with="linespoints",
             graph_title="%(arch)s M=%(M)s",
             xrange="[0:]",
             yrange="[0:]",
             xlabel="cores",
             ylabel="speedup",
             typ=parallel_types, M=Ms, arch=archs, graph_vars=[ "arch", "M" ])

    g.graphs((db, query, init), 
             overlays=[("x", { "plot_title" : "ideal" })],
             output="graphs/speedup_with_ideal_%(arch)s_%(M)s.tex",
             gpl_file="graphs/speedup_with_ideal_%(arch)s_%(M)s.gpl",
             plot_title="%(typ)s",
             plot_with="linespoints",
             graph_title="%(arch)s M=%(M)s",
             xrange="[0:]",
             yrange="[0:]",
             xlabel="cores",
             ylabel="speedup",
             typ=parallel_types, M=Ms, arch=archs, graph_vars=[ "arch", "M" ])
    



