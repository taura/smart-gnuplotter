> smart\_gnuplotter provides a higher level interface to gnuplot,
> making it particularly easy to generate many graphs of many
> plots with a single command.  A basic example is as follows:

> g = smart\_gnuplotter()
> g.graphs('sin(x)')

> You will see the plot of sin(x) on display, just as you will
> when you type
> > plot sin(x)

> to gnuplot.

> More interestingly, you can generate multiple plots by giving
> a parameterized expression and values for the pameters. For
> example,

> g.graphs('sin(%(a)s **x)', a=[1,2,3])**

> will show you three plots sin(1 **x), sin(2** x), and sin(3 **x).
> It is as if you type
> > plot sin(1** x),sin(2 **x),sin(3** x)

> to gnuplot.  You may have multiple parameters, in which case
> all combinations are generated.

> Finally, you can generate multiple graphs by specifying some of
> parameters as "graph\_vars". For example,

> g.graphs('sin(%(a)s **x + %(b)s** pi)',
> > a=[1,2], b=[0.0, 0.2], graph\_vars=['a'])


> will generate two graphs, one for a=1 and the other for a=2.
> Each graph has two plots, one for b=0.0 and the other for 0.2

> You can give to the first argument either
> (1) python string (e.g., 'sin(x)', '"data.txt"', '"< cut -b 9-19 file.txt"'),
> which are simply passed to gnuplot's plot command
> (2) python list, which are passed to gnuplot as in-place data (plot '-')
> (3) python tuple, which are treated as q query to sqlite3 database
> and the query results are passed to gnuplot as in-place data

> The last feature, combined with the parameterization, makes it
> particularly powerful to show data in database from various angles
> and with various data selection criterion.

> You may overlay multiple different plots in the following step.
> g.set\_graph\_attrs()
> g.add\_plots('sin(%(a)s **x)', a=[1,2])
> g.add\_plots('%(b)s** x **x', b=[3,4])
> g.show\_graphs()**

> Essentially, g.graphs(expr) is a shortcut of the above

> g.set\_graph\_attrs()
> g.add\_plots(expr)
> g.show\_graphs()

> There are ways to specify whatever attributes you can specify with
> gnuplot.  Changing a terminal for all graphs takes a single line.
> See the explanation of the following methods for details.

> set\_graph\_attrs()
> add\_plots()