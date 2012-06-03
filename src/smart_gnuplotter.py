import os,sqlite3,types,sys,re

dbg=0

def Es(s):
    sys.stderr.write(s)

class smart_gnuplotter:
    def __init__(self):
        self.exit_on_error = 1
        self.default_terminal = "wxt"
        self.default_pause = -1
        self.default_functions = []
        self.default_aggregates = []
        self.default_collations = []
        self.gpl_file_counter = 0
        
    def open_sql(self, database, init_script, init_file, 
                 functions, aggregates, collations):
        co = sqlite3.connect(database)
        if functions is None: 
            functions = self.default_functions
        else:
            functions = self.default_functions + functions 
        if aggregates is None: 
            aggregates = self.default_aggregates
        else:
            aggregates = self.default_aggregates + aggregates 
        if collations is None: 
            collations = self.default_collations
        else:
            collations = self.default_collations + collations 
        for name,arity,f in functions:
            co.create_function(name, arity, f)
        for name,arity,f in aggregates:
            co.create_aggregate(name, arity, f)
        for name,f in collations:
            co.create_aggregate(name, f)
        if init_script != "":
            co.executescript(init_script)
        if init_file != "":
            fp = open(init_file, "rb")
            script = fp.read()
            fp.close()
            co.executescript(script)
        return co

    def parse_query_expr(self, expr):
        database = expr[0]
        query = expr[1]
        init_script = ""
        init_file = ""
        functions = None
        aggregates = None
        collations = None
        if len(expr) > 2:
            init_script = expr[2]
        if len(expr) > 3:
            init_file = expr[3]
        if len(expr) > 4:
            functions = expr[4]
        if len(expr) > 5:
            aggregates = expr[5]
        if len(expr) > 6:
            collations = expr[6]
        return database,query,init_script,init_file,functions,aggregates,collations
        

    def do_sql(self, database, query, init_script="", init_file="",
               functions=None, aggregates=None, collations=None, 
               single_row=0, single_col=0):
        """
        essentially, it behaves like:
            sqlite3 -init init_file database query
        but it does it in python
        """
        if dbg>=3:
            Es("   do_sql(database=%s,query=%s,init_script=%s,init_file=%s,single_row=%s,single_col=%s)\n" 
               % (database, query, init_script, init_file, single_row, single_col))
        co = self.open_sql(database, init_script, init_file, functions, aggregates, collations)
        if single_row and single_col:
            for (result,) in co.execute(query):
                break
        elif single_row and single_col == 0:
            for result in co.execute(query):
                break
        elif single_row == 0 and single_col:
            result = []
            for (x,) in co.execute(query):
                result.append(x)
        elif single_row == 0 and single_col == 0:
            result = []
            for x in co.execute(query):
                result.append(x)
        else:
            assert 0, (single_row, single_col)
        co.close()
        return result

    def set_graph_attr(self, attr, graph_binding, gpl):
        self.wp = open(gpl, "wb")
        self.wp.write("%s\n" % attr)
        self.args = []

    def run_gnuplot(self, filename):
        cmd = "gnuplot %s" % filename
        if dbg>=1: Es("%s\n" % cmd)
        return os.system(cmd)

    def remove(self, filename):
        if dbg>=1:
            Es("remove %s\n" % filename)
        os.remove(filename)

    def prompt(self):
        if self.default_pause < 0:
            Es("'s' to suppress future prompts, 'q' to quit now, "
               "or else to continue [s/q/other]? ")
            line = sys.stdin.readline()
            Es("\n")
            if line[0:1] == "q":
                return 1
            elif line[0:1] == "s":
                self.default_pause = 0
        return 0

    def is_epslatex(self, terminal):
        if re.match(" *epslatex", terminal):
            return 1
        else:
            return 0

    def fix_include_graphics(self, tex):
        tex2 = "%s.tmp" % tex
        fp = open(tex, "rb")
        x = fp.read()
        fp.close()
        y = re.sub("includegraphics\{([^\}]+)\}", 
                   r"includegraphics{\1.eps}", x)
        wp = open(tex2, "wb")
        wp.write(y)
        wp.close()
        os.rename(tex2, tex)

    def show_graph(self, terminal, output, pause, gpl, remove):
        if dbg>=3:
            Es("  show_graph\n")
        self.write_tics(self.args)
        self.write_curves_canonical(self.args)
        self.wp.write("pause %d\n" % pause)
        self.wp.close()
        r = self.run_gnuplot(gpl)
        if r == 0:
            r = self.prompt()
            if remove: self.remove(gpl)
            if self.is_epslatex(terminal):
                self.fix_include_graphics(output)
        else:
            Es("error: gnuplot command failed with %d, file '%s' is "
               "left for your inspection\n" % (r, gpl))
        return r
        

    def x_is_symbol(self, data):
        for row in data:
            try:
                float(row[0])
            except:
                return 1
        return 0
            
    def mk_x_idx(self, data):
        D = {}
        for i,row in enumerate(data):
            x = row[0]
            D[x] = i
        return D

    def write_tics(self, curves):
        if dbg>=3:
            Es("   write_tics(curves=%s)\n" % curves)
        wp = self.wp
        A = []
        for expr,attr,bindings in curves:
            for bind in bindings:
                data = None
                if type(expr) is types.ListType:
                    data = expr
                elif type(expr) is types.TupleType:
                    X = self.parse_query_expr(expr)
                    database,query,init_script,init_file,functions,aggregates,collations = X
                    data = self.do_sql((database % bind), (query % bind),
                                       (init_script % bind), (init_file % bind),
                                       functions, aggregates, collations)
                if data is not None:
                    if self.x_is_symbol(data):
                        for i,row in enumerate(data):
                            A.append('"%s" %d' % (row[0], i))
        if len(A) > 0:
            wp.write('set xtics (%s)\n' % ",".join(A))

    def write_curves_canonical(self, curves):
        """
        curves : list of (expr_template, attr_template, bindings)

        (1) expr_template specifies what to plot. it may be:
        - a string (e.g., 'x', '"a.dat"')
        - a python list of two numbers (e.g., [(1,2),(2,4),(3,9)])
        - tuple of database filename, and an SQL query (e.g., ("a.db", "select x,y from t"))
        
        each may contain a placeholder, like %(a)s which is substituted
        by bindings argument

        (2) attr_template is a string specifying attributes of the curve.
        in short, it come after 'plot xxx' 

        (3) bindings is a list of dictionaries. each element of the list
        (a dictionary) must supply values of placeholders.

        given these parameters, it writes an appropriate 'plot' command
        of gnuplot to write all curves obtained by instantiating 
        expr_template and attr_template, by bindings.
        e.g., 

        curves = [ ('%(a)s * x', 'title "%(a)x"', [ {"a":1}, {"a":2} ]),
                   ('%(b)s / x', 'title "x/%(b)"', [ {"b":3}, {"b":4} ]) ]
        will generate:
         plot 1*x title "1x", 2*x title "2x", 3/x title "3/x", 4/x title "4/x"

        """
        if dbg>=3:
            Es("  write_curves_canonical(%s)\n" % curves)
        wp = self.wp
        wp.write("plot ")
        C = []
        for i,(expr,attr,bindings) in enumerate(curves):
            for bind in bindings:
                if type(expr) is types.ListType:
                    # list of data
                    c = "'-'"
                elif type(expr) is types.TupleType:
                    # (database,query)
                    c = "'-'"
                else:
                    assert(type(expr) is types.StringType), expr
                    c = expr % bind
                C.append("%s %s" % (c, (attr % bind)))
        wp.write("%s\n" % ", ".join(C))
        for expr,attr,bindings in curves:
            for bind in bindings:
                data = None
                if type(expr) is types.ListType:
                    data = expr
                elif type(expr) is types.TupleType:
                    X = self.parse_query_expr(expr)
                    database,query,init_script,init_file,functions,aggregates,collations = X
                    data = self.do_sql((database % bind), (query % bind),
                                       (init_script % bind), (init_file % bind),
                                       functions, aggregates, collations)
                if data is not None:
                    if self.x_is_symbol(data):
                        idx = self.mk_x_idx(data)
                        for row in data:
                            x = row[0]
                            fmt = " ".join([ "%s" ] * len(row)) + "\n"
                            wp.write(fmt % ((idx[x],) + row[1:]))
                    else:
                        for row in data:
                            fmt = " ".join([ "%s" ] * len(row)) + "\n"
                            wp.write(fmt % row)
                    wp.write("e\n")

    def expand_vars_rec(self, K, V, A):
        """
        K : a dictionary containing variables to expand
        V : a dictionary containing variables that have been bound
        A : a list to accumulate all bindings
        """
        if len(K) == 0:
            A.append(V.copy())
        else:
            k,vals = K.popitem()
            for v in vals:
                assert (k not in V), (k, V)
                V[k] = v
                self.expand_vars_rec(K, V, A)
                del V[k]
            K[k] = vals
        return A

    def expand_vars(self, K):
        """
        e.g., 
        expand_vars({ "a" : [1,2], "b" : [3,4] })

        ==> [ { "a" : 1, "b" : 3 },
              { "a" : 1, "b" : 4 },
              { "a" : 2, "b" : 3 },
              { "a" : 2, "b" : 4 } ]

        """
        R = []
        for D in self.expand_vars_rec(K, {}, []):
            E = D.copy()
            for k,v in D.items():
                if type(v) is types.TupleType:
                    for i in range(len(v)):
                        ki = "%s[%d]" % (k, i)
                        vi = v[i]
                        E[ki] = vi
            R.append(E)
        return R

    def add_curves(self, expr, curve_attr, variables, graph_binding):
        """
        expr : a string specifying what to plot. may contain placeholders
        curve_attr : a string specifying the attribute of the curve.
                     may contain placeholders
        variables : a dictionary each entry of which specifies a variable
                    and its possible values

        add curves for all combinations of variables, so it 
        will be written when show_graph method is called
        """
        if dbg>=3:
            Es("  add_curves(expr=%s,curve_attr=%s,variables=%s,graph_binding=%s)" 
               % (expr, curve_attr, variables, graph_binding))
        curve_bindings = self.expand_vars(variables)
        # merge graph binding and curve_binding
        for curve_binding in curve_bindings:
            curve_binding.update(graph_binding)
        self.args.append((expr, curve_attr, curve_bindings))

    def add_many_curves(self, curves, graph_binding):
        """
        curves : list of (expr, curve_attr, variables)
        see add_curves for the types of each field
        """
        for expr,curve_attr,variables in curves:
            self.add_curves(expr, curve_attr, variables, graph_binding)

    def graph_canonical(self, terminal, output, graph_attr, graph_binding, 
                        curves, pause, gpl_file):
        """
        write a single graph (may contain many curves).
        curves : see add_many_curves for its type
        graph_attr : a string passed to gnuplot prior to plot
        """
        if dbg>=3:
            Es(" graph_canonical(graph_attr=%s,graph_binding=%s,curves=%s)" 
               % (graph_attr, graph_binding, curves))
        if gpl_file is None:
            remove = 1
            gpl_file = "tmp_%d.gpl" % self.gpl_file_counter
            self.gpl_file_counter = self.gpl_file_counter + 1
        else:
            remove = 0
        gpl = gpl_file % graph_binding
        self.set_graph_attr(graph_attr, graph_binding, gpl)
        self.add_many_curves(curves, graph_binding)
        r = self.show_graph(terminal, output, pause, gpl, remove)
        return r

    def graphs_canonical(self, terminal_template, output_template, 
                         graph_attr_template, graph_variables, curves, 
                         pause, gpl_file):
        if dbg>=3:
            Es("graphs_canonical(graph_attr_template=%s,graph_variables=%s,curves=%s)" % 
               (graph_attr_template, graph_variables, curves))
        graph_bindings = self.expand_vars(graph_variables)
        if dbg>=3:
            Es(" graph_bindings=%s" % graph_bindings)
        for graph_binding in graph_bindings:
            graph_attr = graph_attr_template % graph_binding
            terminal = terminal_template % graph_binding
            output = output_template % graph_binding
            r = self.graph_canonical(terminal, output, graph_attr, 
                                     graph_binding, curves, pause, gpl_file)
            if r: 
                return r      # NG
        return 0                # OK

    def graphs(self, expr_template, 
               curve_attr="",   # attribute of each curve
               graph_attr="",   # attribute of the graph
               graph_vars=None, # variables in graph_attr
               overlays=None, 
               pause=None,
               graph_title=None,
               terminal=None,
               output=None,
               xrange=None,
               yrange=None,
               xlabel=None,
               ylabel=None,
               boxwidth=None,
               curve_title=None,
               curve_with=None,
               gpl_file=None,
               **variables):
        if overlays is None: overlays = []
        if graph_vars is None: graph_vars = []
        if pause is None:
            pause = self.default_pause
        if graph_title is not None: 
            graph_attr = 'set title "%s"\n%s' % (graph_title, graph_attr)
        if terminal is None: terminal = self.default_terminal
        if terminal is not None: 
            graph_attr = 'set terminal %s\n%s' % (terminal, graph_attr)
        if output is not None: 
            graph_attr = 'set output "%s"\n%s' % (output, graph_attr)
        if xrange is not None: 
            graph_attr = 'set xrange %s\n%s' % (xrange, graph_attr)
        if yrange is not None: 
            graph_attr = 'set yrange %s\n%s' % (yrange, graph_attr)
        if xlabel is not None: 
            graph_attr = 'set xlabel "%s"\n%s' % (xlabel, graph_attr)
        if ylabel is not None: 
            graph_attr = 'set ylabel "%s"\n%s' % (ylabel, graph_attr)
        if boxwidth is not None: 
            graph_attr = 'set boxwidth %s\n%s' % (boxwidth, graph_attr)
        if curve_title is not None:
            curve_attr = 'title "%s" %s' % (curve_title, curve_attr)
        if curve_with is not None:
            curve_attr = 'with %s %s' % (curve_with, curve_attr)
        graph_variables = {}
        curve_variables = {}
        for v,vals in variables.items():
            if v in graph_vars:
                graph_variables[v] = vals
            else:
                curve_variables[v] = vals
        curves = [ (expr_template, curve_attr, curve_variables) ]
        for expr,mod in overlays:
            curves.append((expr, mod, {}))
        r = self.graphs_canonical(terminal, output, graph_attr, 
                                  graph_variables, curves, pause, gpl_file)
        if r and self.exit_on_error:
            if os.WIFEXITED(r):
                sys.exit(os.WEXITSTATUS(r))
            else:
                sys.exit(1)
        else:
            return r

def main():
    g = smart_gnuplotter()
    g.graphs("sin(%(a)s * x) + %(b)s", 
             curve_attr='title "sin(%(a)sx)+%(b)s"',
             graph_attr='set title "b=%(b)s"',
             graph_vars=["b"],
             overlays=[("x",""),("0","")], a=[2,3], b=[1,2])

