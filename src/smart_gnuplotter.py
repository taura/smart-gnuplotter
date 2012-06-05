import os,sqlite3,types,sys,re,math,traceback

dbg=0

class smart_gnuplotter:
    def __init__(self):
        self.exit_on_error = 1
        self.default_terminal = None
        self.default_output = None
        self.default_pause = -1
        self.default_functions = []
        self.default_aggregates = [ ("cimin", 2, cimin), ("cimax", 2, cimax) ]
        self.default_collations = []
        self.gpl_file_counter = 0
        
    def __Es(self, s):
        sys.stderr.write(s)

    def __open_sql(self, database, init_statements, init_file, 
                 functions, aggregates, collations):
        """
        database    : string : filename of an sqlite3 database 
        init_statements : string : sql statement(s) to run
        init_file   : string : filename containing sql statement(s)
        functions   : list of (name, arity, function) specifying
                      user defined functions. they are passed as
                      create_function(name, arity, function)
        aggregates  : list of (name, arity, function) specifying
                      user defined aggregates. they are passed as
                      create_aggregate(name, arity, function)
        collations  : list of (name, function) specifying
                      user defined collations. they are passed as
                      create_collation(name, function)
        connect to sqlite3 database database, 
        add user defined functions/aggregates/callations, 
        run init_statements and init_file,
        and return the connection object
        """
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
        if init_statements != "":
            co.executescript(init_statements)
        if init_file != "":
            fp = open(init_file, "rb")
            script = fp.read()
            fp.close()
            co.executescript(script)
        return co

    def __parse_query_expr(self, expr):
        """
        expr : a tuple of 2-7 elements
        supply defaults for missing elements and always
        return a 7-elements tuple
        database,query,init_statements,init_file,functions,aggregates,collations
        """
        database = expr[0]
        query = expr[1]
        init_statements = ""
        init_file = ""
        functions = []
        aggregates = []
        collations = []
        if len(expr) > 2:
            init_statements = expr[2]
        if len(expr) > 3:
            init_file = expr[3]
        if len(expr) > 4:
            functions = expr[4]
        if len(expr) > 5:
            aggregates = expr[5]
        if len(expr) > 6:
            collations = expr[6]
        return database,query,init_statements,init_file,functions,aggregates,collations
        

    def do_sql(self, database, query, init_statements="", init_file="",
               functions=None, aggregates=None, collations=None, 
               single_row=0, single_col=0):
        """
        database    : string : filename of an sqlite3 database 
        init_statements : string : sql statement(s) to run
        init_file   : string : filename containing sql statement(s)
        functions   : list of (name, arity, function) specifying
                      user defined functions. they are passed as
                      create_function(name, arity, function)
        aggregates  : list of (name, arity, function) specifying
                      user defined aggregates. they are passed as
                      create_aggregate(name, arity, function)
        collations  : list of (name, function) specifying
                      user defined collations. they are passed as
                      create_collation(name, function)
        connect to sqlite3 database database, 
        add user defined functions/aggregates/callations, 
        run init_statements and init_file,
        execute the query,
        and return the result.

        when single_row == 0 and single_col == 0:
          it is returned as a list of tuples
        when single_row == 1,
          it is assumed that the result has only a single row,
          and that row is returned
        when single_col == 1,
          it is assumed that each row has a single column
          and each element of the list becomes that column
          instead of a singleton tuple.
        """
        if dbg>=3:
            self.__Es("   do_sql(database=%s,query=%s,init_statements=%s,init_file=%s,functions=%s,aggregates=%s,collations=%s,single_row=%s,single_col=%s)\n" 
               % (database, query, init_statements, init_file, 
                  functions, aggregates, collations, single_row, single_col))
        co = self.__open_sql(database, init_statements, init_file, 
                             functions, aggregates, collations)
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

    def __write_graph_attr(self, terminal, output, attr, gpl):
        """
        terminal : None or string : specifies gnuplot terminal
        output   : None or string : specifies gnuplot output filename
        attr     : string : specifies graph attributes 
        graph_binding : string : specifies graph attributes 
        gpl      : gnuplot filename
        """
        wp = open(gpl, "wb")
        if terminal is not None: 
            wp.write('set terminal %s\n' % terminal)
        if output is not None: 
            wp.write('set output "%s"\n' % output)
        wp.write("%s\n" % attr)
        self.args = []
        return wp

    def __run_gnuplot(self, filename):
        """
        run gnuplot filename
        and return the status
        """
        cmd = "gnuplot %s" % filename
        if dbg>=1: self.__Es("%s\n" % cmd)
        return os.system(cmd)

    def __remove(self, filename):
        if dbg>=1:
            self.__Es("remove %s\n" % filename)
        os.remove(filename)

    def __safe_int(self, line):
        try:
            return int(line)
        except ValueError:
            return None

    def __get_terminal_type(self, terminal):
        """
        terminal : string : specifies thee full gnuplot terminal string,
         such as "epslatex size 10cm,5cm"

        extract the 'type' from the terminal spec ("epslatex" from
        "epslatex size 10cm,5cm"
        """
        return terminal.split()[0].lower()

    def __is_epslatex(self, terminal):
        if terminal is None: return 0
        if self.__get_terminal_type(terminal) == "epslatex":
            return 1
        else:
            return 0

    def __is_display(self, terminal):
        if terminal is None: return 1
        t = self.__get_terminal_type(terminal)
        if t == "wxt" or t == "x11" or t == "xterm":
            return 1
        else:
            return 0

    def __prompt(self, terminal, pause):
        """
        terminal : string : specifies ther terminal of the last
                   invocation of guplot
        pause    : integer : specifies how much the last 
                   invocation of guplot paused

        if the last gnuplot terminal is a display (wxt, x11, xterm)
        and the gnuplot waits for the key input (pause < 0), 
        then it asks what to do in similar situations later.
        's' : we never 'pause' gnuplot
        'q' : quit immeidately
        number : let gnuplot pause the specified number of seconds 
        """
        if self.__is_display(terminal) and pause < 0:
            self.__Es("'s' to suppress future prompts, 'q' to quit now, "
               "a <number> to set pause to it, "
               "or else to continue [s/q/<number>/other]? ")
            line = sys.stdin.readline()
            self.__Es("\n")
            if line[0:1] == "q":
                return 1
            elif line[0:1] == "s":
                self.default_pause = 0
            else:
                x = self.__safe_int(line)
                if x is not None:
                    self.default_pause = x
        return 0

    def __extend_filename(self, output, terminal):
        """
        output : None or string : filename of the output
        terminal : None or string : gnuplot terminal 
        attach extention to output, based on terminal.
        e.g., output="x", terminal="epslatex" -> x.tex
        """
        if output is None: return output
        if terminal is None: return output
        terminal_type = terminal.split()[0]
        ext_D = {
            "epslatex" : ".tex",
            "latex"    : ".tex",
            "fig"     : ".tex",
            "texdraw" : ".tex",
            "pslatex" : ".tex",
            "pstex"   : ".tex",
            "postscript" : ".eps",
            "jpeg"    : ".jpg",
            "svg"     : ".svg",
            "gif"     : ".gif",
            "png"     : ".png", }
        ext = ext_D.get(terminal_type, "")
        return output + ext

    def __fix_include_graphics(self, tex):
        """
        tex : string : filename output by epslatex
        fix the \includegraphics{file} line of the tex file
        to \includegraphics{file.eps}.  this is necessary
        to make it possible to load this file with dvipdfm
        driver
        """
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

    def __x_is_symbol(self, data):
        for row in data:
            try:
                float(row[0])
            except:
                return 1
        return 0
            
    def __mk_x_idx(self, data):
        D = {}
        for i,row in enumerate(data):
            x = row[0]
            D[x] = i
        return D

    def __write_tics(self, wp, plots):
        """
        plots : list of (expression, string, list of tuples)
        expression is either string, list, or uple specifying what to plot

        examine whether the x-axis of the data is symbolic, and if so,
        it generates an appropriate 
        set xtics (...) 
        line in the gnuplot command file
        """
        if dbg>=3:
            self.__Es("   write_tics(plots=%s)\n" % plots)
        A = []
        for expr,attr,bindings in plots:
            for bind in bindings:
                data = None
                if type(expr) is types.ListType:
                    data = expr
                elif type(expr) is types.TupleType:
                    X = self.__parse_query_expr(expr)
                    database,query,init_statements,init_file,functions,aggregates,collations = X
                    data = self.do_sql((database % bind), (query % bind),
                                       (init_statements % bind), (init_file % bind),
                                       functions, aggregates, collations)
                if data is not None:
                    if self.__x_is_symbol(data):
                        for i,row in enumerate(data):
                            A.append('"%s" %d' % (row[0], i))
        if len(A) > 0:
            wp.write('set xtics (%s)\n' % ",".join(A))


    def __write_plots_canonical(self, wp, plot, plots):
        """
        plots : list of (expr_template, attr_template, bindings)

        (1) expr_template specifies what to plot. it may be:
        - a string (e.g., 'x', '"a.dat"')
        - a python list of two numbers (e.g., [(1,2),(2,4),(3,9)])
        - tuple of database filename, and an SQL query 
          (e.g., ("a.db", "select x,y from t"))
        
        each may contain a placeholder, like %(a)s which is substituted
        by bindings argument

        (2) attr_template is a string specifying attributes of the plot.
        in short, it come after 'plot xxx' 

        (3) bindings is a list of dictionaries. each element of the list
        (a dictionary) must supply values of placeholders.

        given these parameters, it writes an appropriate 'plot' command
        of gnuplot to write all plots obtained by instantiating 
        expr_template and attr_template, by bindings.
        e.g., 

        plots = [ ('%(a)s * x', 'title "%(a)x"', [ {"a":1}, {"a":2} ]),
                   ('%(b)s / x', 'title "x/%(b)"', [ {"b":3}, {"b":4} ]) ]
        will generate:
         plot 1*x title "1x", 2*x title "2x", 3/x title "3/x", 4/x title "4/x"

        """
        if dbg>=3:
            self.__Es("  write_plots_canonical(%s)\n" % plots)
        wp.write("%s " % plot)
        C = []
        for i,(expr,attr,bindings) in enumerate(plots):
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
        for expr,attr,bindings in plots:
            for bind in bindings:
                data = None
                if type(expr) is types.ListType:
                    data = expr
                elif type(expr) is types.TupleType:
                    X = self.__parse_query_expr(expr)
                    db,qu,init_stmts,init_file,funcs,aggrs,colls = X
                    data = self.do_sql((db % bind), (qu % bind),
                                       (init_stmts % bind), (init_file % bind),
                                       funcs, aggrs, colls)
                # query or python list. generate data in place followed by 'e'
                if data is not None:
                    if self.__x_is_symbol(data):
                        # if x-axis is symbolic, translate each data
                        # into its index
                        idx = self.__mk_x_idx(data)
                        for row in data:
                            x = row[0]
                            fmt = " ".join([ "%s" ] * len(row)) + "\n"
                            wp.write(fmt % ((idx[x],) + row[1:]))
                    else:
                        for row in data:
                            fmt = " ".join([ "%s" ] * len(row)) + "\n"
                            wp.write(fmt % row)
                    wp.write("e\n")

    def __show_graph(self, wp, plot, terminal, output, pause, gpl, remove):
        """
        terminal : None or string : specifies gnuplot terminal
        output : None or string : specifies gnuplot output filename
        pause : integer : specifies how much to pause gnuplot after 
                   showing graph
        gpl : filename to write gnuplot command to 
        remove : 0/1 : 1 if gpl should be removed after gnuplot 
        """
        if dbg>=3:
            self.__Es("  show_graph(terminal=%s,output=%s,pause=%s,gpl=%s,remove=%s)\n"
               % (terminal, output, pause, gpl, remove))
        self.__write_tics(wp, self.args)
        self.__write_plots_canonical(wp, plot, self.args)
        if self.__is_display(terminal):
            if pause is None: pause = self.default_pause
            wp.write("pause %d\n" % pause)
        wp.close()
        r = self.__run_gnuplot(gpl)
        if r == 0:
            r = self.__prompt(terminal, pause)
            if remove: 
                self.__remove(gpl)
            else:
                self.__Es("gnuplot file '%s' is left for your inspection\n" 
                          % gpl)
            if self.__is_epslatex(terminal):
                self.__fix_include_graphics(output)
        else:
            self.__Es("error: gnuplot command failed with %d, file '%s' is "
               "left for your inspection\n" % (r, gpl))
        return r
        
    def __expand_vars_rec(self, K, V, A):
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
                self.__expand_vars_rec(K, V, A)
                del V[k]
            K[k] = vals
        return A

    def __expand_vars(self, K):
        """
        e.g., 
        expand_vars({ "a" : [1,2], "b" : [3,4] })

        ==> [ { "a" : 1, "b" : 3 },
              { "a" : 1, "b" : 4 },
              { "a" : 2, "b" : 3 },
              { "a" : 2, "b" : 4 } ]

        """
        R = []
        for D in self.__expand_vars_rec(K, {}, []):
            E = D.copy()
            for k,v in D.items():
                # when the value is a tuple (e.g., "x" : (3, 4)),
                # register "x[0]" : 3 and "x[1]" : 4 as well
                if type(v) is types.TupleType:
                    for i in range(len(v)):
                        ki = "%s[%d]" % (k, i)
                        vi = v[i]
                        E[ki] = vi
            R.append(E)
        return R

    def __add_plots(self, expr, plot_attr, variables, graph_binding):
        """
        expr : string, list, tuple : specifies what to plot. 
               may contain placeholders
        plot_attr : string : specifies the attribute of the plot.
                     may contain placeholders
        variables : a dictionary each entry of which specifies a variable
                    and its possible values 
                    (e.g., { "a" : [1,2,3], "b" : [4,5,6] })

        add plots for all combinations of variables, so it 
        will be written when show_graph method is called
        """
        if dbg>=3:
            self.__Es("  add_plots(expr=%s,plot_attr=%s,variables=%s,graph_binding=%s)\n" 
               % (expr, plot_attr, variables, graph_binding))
        plot_bindings = self.__expand_vars(variables)
        # merge graph binding and plot_binding
        for plot_binding in plot_bindings:
            plot_binding.update(graph_binding)
        self.args.append((expr, plot_attr, plot_bindings))

    def __add_many_plots(self, plots, graph_binding):
        """
        plots : list of (expr, plot_attr, variables)
        see add_plots for the types of each field
        """
        for expr,plot_attr,variables in plots:
            self.__add_plots(expr, plot_attr, variables, graph_binding)

    def __graph_canonical(self, plot, terminal, output, 
                          graph_attr, graph_binding, 
                          plots, pause, gpl_file, save_gpl):
        """
        terminal : string or None : specifies gnuplot terminal
        output : string or None : specifies gnuplot output
        graph_attr : string : specifies graph attribute template
        graph_binding : dictionary : specifies binding to substitute 
                        graph_attr
        plots : list of plot specs :
        pause : 
        gpl_file : 
        write a single graph (may contain many plots).
        plots : see add_many_plots for its type
        graph_attr : a string passed to gnuplot prior to plot
        """
        if dbg>=3:
            self.__Es(" graph_canonical(graph_attr=%s,graph_binding=%s,plots=%s)\n" 
               % (graph_attr, graph_binding, plots))
        if gpl_file is None:
            if save_gpl:
                remove = 0
            else:
                remove = 1
            gpl_file = "tmp_%d.gpl" % self.gpl_file_counter
            self.gpl_file_counter = self.gpl_file_counter + 1
        else:
            remove = 0
        wp = self.__write_graph_attr(terminal, output, graph_attr, gpl_file)
        self.__add_many_plots(plots, graph_binding)
        r = self.__show_graph(wp, plot, terminal, output, pause, gpl_file, remove)
        return r

    def __graphs_canonical(self, plot, terminal_template, output_template, 
                           graph_attr_template, graph_variables, 
                           pause, plots, gpl_file_template, leave_gpl):
        if dbg>=3:
            self.__Es("graphs_canonical(graph_attr_template=%s,graph_variables=%s,plots=%s)\n" % 
               (graph_attr_template, graph_variables, plots))
        graph_bindings = self.__expand_vars(graph_variables)
        if dbg>=3:
            self.__Es(" graph_bindings=%s\n" % graph_bindings)
        for graph_binding in graph_bindings:
            graph_attr = graph_attr_template % graph_binding
            # instantiate template
            if terminal_template is None:
                terminal = None
            else:
                terminal = terminal_template % graph_binding
            if output_template is None:
                if dbg>=3:
                    self.__Es("  output_template=%s, graph_variables=%s\n"
                       % (output_template, graph_variables))
                if self.__is_display(terminal):
                    template = None
                else:
                    keys = [ ("_%%(%s)s" % x) for x in graph_variables.keys() ]
                    template = "out%s" % "".join(keys)
                    if dbg>=3:
                        self.__Es("   output_template->%s, graph_binding=%s\n" 
                           % (new_template, graph_binding))
            else:
                template = output_template
            if template is None:
                output = None
            else:
                output = template % graph_binding
                output = self.__extend_filename(output, terminal)
            if gpl_file_template is None:
                gpl_file = None
            else:
                gpl_file = gpl_file_template % graph_binding
            r = self.__graph_canonical(plot, terminal, output, graph_attr, 
                                       graph_binding, plots, pause, gpl_file,
                                       leave_gpl)
            if r: return r      # NG
        return 0                # OK

    def graphs(self, expr_template, 
               plot="plot", 
               terminal=None,
               output=None,
               graph_title=None,
               xrange=None,
               yrange=None,
               xlabel=None,
               ylabel=None,
               boxwidth=None,
               graph_attr="",   # attribute of the graph
               graph_vars=None, # variables in graph_attr
               pause=None,
               plot_title=None,
               plot_with=None,
               using=None,
               plot_attr="",   # attribute of each plot
               overlays=None, 
               gpl_file=None,
               leave_gpl=0,
               **variables):
        """
        expr_template : string, python list, or tuple :
          specifies what to plot (see below)
        plot : "plot" or "splot"
        terminal : None or string :
          specifies terminal used (e.g., epslatex size 10cm,5cm)
        output : None or string : 
          specifies output filename or its prefix
        graph_title : None or string : 
          specifies the graph title
        xrange : None or string : 
          specifies xrange (e.g., "[0:]")
        yrange : None or string : 
          specifies yrange (e.g., "[0:]")
        boxwidth : None or string : 
          set boxwidth, effective only when you use boxes
        graph_attr : string : 
          specifies any string that comes before plot command
        graph_vars : list of strings : 
          specifies which variable to use to generate
        plot_title : None or string :
          specifies plot title
        plot_with : None or string :
          specifies style to plot plots (e.g., "boxes", "lines")
        using : None or string :
          specifies columns to plot plots (e.g., "2", "1:2")
        plot_attr : None or string :
          specifies any attribute of plots 
        overlays : list of (expression, modifier) 
          specifies plots to overlay
        leave_gpl : 0/1
          if 1, it leaves the gnuplot file for your inspection
        gpl_file : None or string :
          specifies the filename of (temporary) files to write
          gnuplot commands to; implies leave_gpl = 1
        """
        if terminal is None: terminal = self.default_terminal
        if output is None: output = self.default_output
        if graph_title is not None: 
            graph_attr = 'set title "%s"\n%s' % (graph_title, graph_attr)
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
        if graph_vars is None: graph_vars = []
        if plot_title is not None:
            plot_attr = 'title "%s" %s' % (plot_title, plot_attr)
        if plot_with is not None:
            plot_attr = 'with %s %s' % (plot_with, plot_attr)
        if using is not None:
            plot_attr = 'using %s %s' % (using, plot_attr)
        if overlays is None: overlays = []
        graph_variables = {}
        plot_variables = {}
        for v,vals in variables.items():
            if v in graph_vars:
                graph_variables[v] = vals
            else:
                plot_variables[v] = vals
        plots = [ (expr_template, plot_attr, plot_variables) ]
        for expr,mod in overlays:
            plots.append((expr, mod, {}))
        r = self.__graphs_canonical(plot, terminal, output, graph_attr, 
                                    graph_variables, pause, plots, gpl_file,
                                    leave_gpl)
        if r != 0 and self.exit_on_error:
            if os.WIFEXITED(r):
                sys.exit(os.WEXITSTATUS(r))
            else:
                sys.exit(1)
        else:
            return r


# -------------------------

class confidence_interval:

    def f(self, t, nu):
        A = math.gamma((nu + 1) * 0.5)
        B = math.sqrt(nu * math.pi) * math.gamma(nu * 0.5)
        C = math.pow(1 + t * t / nu, -(nu + 1) * 0.5)
        return (A * C) / B 

    def rk_step(self, f, t, dt):
        k1 = f(t)
        k2 = f(t + dt * 0.5)
        k3 = f(t + dt * 0.5)
        k4 = f(t + dt)
        dy = dt / 6.0 * (k1 + 2.0*k2 + 2.0*k3 + k4)
        return dy

    def find_x(self, f, a, dt, J):
        """
        return x s.t. int_a^x f(t)dt = J
        
        """
        # print "find_x(f, %f, %f, %f)" % (a, dt, J)
        t = a
        I = 0.0
        while 1:
            dI = self.rk_step(f, t, dt)
            if I + dI < J:
                I += dI
                t += dt
            elif dt < 1.0E-6:
                return t
            else:
                return self.find_x(f, t, dt * 0.1, J - I)

    def t_table(self, freedom, significance_level):
        """
        freedom : int 
        significance_level : float : 0.05, 0.01, etc.

        find a such that 
        int_{-a}^a f(t, freedom) dt = 1 - significance_level
        """
        g = lambda t: self.f(t, freedom)
        return self.find_x(g, 0.0, 0.01, (1 - significance_level) * 0.5)

    def confidence_interval(self, X, significance_level):
        """
        return (mu, dm) s.t.  m \pm dm is the confidence interval
        of the average of probability density from which X was drawn,
        with the specified significance level 
        """
        n = len(X)
        # empirical average
        mu = sum(X) / float(n)
        # unbiased variance
        U = sum([ (x - mu) * (x - mu) for x in X ]) / float(n - 1)
        t = self.t_table(n - 1, significance_level)
        dm = t * U / math.sqrt(n)
        return (mu, dm)

    def __init__(self):
        self.X = []
        self.significance_level = 0.05

    def step(self, value, sl):
        self.significance_level = sl
        self.X.append(value)

    def finalize(self):
        try:
            return self.finalize_()
        except Exception,e:
            #sys.stderr.write("Exception %s\n" % (e.args,))
            traceback.print_exc()
            raise

class cimax(confidence_interval):
    def finalize_(self):
        mu,dm = self.confidence_interval(self.X, self.significance_level)
        return mu + dm

class cimin(confidence_interval):
    def finalize_(self):
        mu,dm = self.confidence_interval(self.X, self.significance_level)
        return mu - dm

def __main():
    co = sqlite3.connect(":memory:")
    co.create_aggregate("cmin", 2, cmin)
    co.create_aggregate("cmax", 2, cmax)
    co.execute("create table foo(a, b)")
    co.execute("insert into foo values(1, 2)")
    co.execute("insert into foo values(1, 3)")
    co.execute("insert into foo values(1, 4)")
    co.execute("insert into foo values(1, 5)")
    x = co.execute("select cmin(b, 0.05),cmax(b, 0.05) from foo")
    return x.fetchall()


def __main():
    g = smart_gnuplotter()
    g.graphs("sin(%(a)s * x) + %(b)s", 
             plot_attr='title "sin(%(a)sx)+%(b)s"',
             graph_attr='set title "b=%(b)s"',
             graph_vars=["b"],
             overlays=[("x",""),("0","")], a=[2,3], b=[1,2])

