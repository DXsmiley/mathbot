import asyncio
import calculator.interpereter
import calculator.parser
import calculator.runtime
import calculator.bytecode
import calculator.errors
import calculator.runtime
import calculator.formatter
import sympy
import json
import traceback
import re


ERROR_TEMPLATE = '''\
On line {line_num} at position {position}
{prev}
{cur}
{carat}'''


TAB_WITH = 8


class AccessGlobalMissHook:

    def __init__(self, interpereter, linker):
        self.interpereter = interpereter
        self.linker = linker

    def __call__(self, name):
        missing_bytecode = calculator.runtime.load_on_demand(name)
        if not missing_bytecode:
            return False
        frozen = self.interpereter.state_freeze()
        self.interpereter.stack = [None]
        self.interpereter.place = self.linker.add_segment(missing_bytecode)
        self.interpereter.run()
        self.interpereter.state_thaw(frozen)
        self.interpereter.place -= 3 # Go back to the instruction to load the value
        return True


class Terminal:

    def __init__(self,
                 allow_special_commands=False,
                 retain_cache=True,
                 output_limit=None,
                 yield_rate=100,
                 load_on_demand=True,
                 colour_output=False,
                 runtime_protection_level=0):
        self.show_tree = False
        self.show_parsepoint = False
        self.show_result_type = False
        self.linker = calculator.bytecode.Linker()
        self.allow_special_commands = allow_special_commands
        self.load_on_demand = load_on_demand
        self.colour_output = colour_output
        if not load_on_demand:
            try:
                runtime = calculator.runtime.prepare_runtime()
                self.linker.add_segments(runtime)
            except calculator.parser.ParseFailed as e:
                print('RUNTIME ISSUE: Parse error')
                print(format_error_place(calculator.runtime.LIBRARY_CODE, e.position))
                raise e
            except calculator.parser.TokenizationFailed as e:
                print('RUNTIME ISSUE: Tokenization error')
                print(format_error_place(calculator.runtime.LIBRARY_CODE, e.position))
                raise e
        hooks = {}
        self.interpereter = calculator.interpereter.Interpereter(
            self.linker.constructed(),
            yield_rate=yield_rate,
            hooks=hooks
        )
        if load_on_demand:
            hooks['access-global-miss'] = AccessGlobalMissHook(self.interpereter, self.linker)
        else:
            try:
                self.interpereter.run(
                    assignment_auth_level=runtime_protection_level,
                    assignment_protection_level=runtime_protection_level)
            except Exception:
                print('Error during library loading. Re-running with trace.')
                temp_interp = calculator.interpereter.Interpereter(
                    self.linker.constructed(),
                    yield_rate=yield_rate,
                    trace=True
                )
                temp_interp.run()
        self.line_count = 0
        self.retain_cache = retain_cache
        self.output_limit = output_limit

    def execute(self, code):
        loop = asyncio.get_event_loop()
        future = self.execute_internal(code)
        return loop.run_until_complete(future)

    async def execute_async(self, code, **kwargs):
        return await self.execute_internal(code)

    async def execute_internal(self, line, **kwargs):
        ''' Runs some code.
            Returns a string-bool tuple.
            The string is the output to display to the user.
            The bool is True if nothing went wrong.
        '''
        output = []
        details = {}
        def prt(*args):
            args = list(args)
            for i, v in enumerate(args):
                try:
                    args[i] = calculator.formatter.format(v, limit = self.output_limit)
                except Exception:
                    print(e)
            output.append(' '.join(map(str, args)))
        self.line_count += 1
        worked = True
        if self.allow_special_commands and line == ':tree':
            self.show_tree = not self.show_tree
        elif self.allow_special_commands and line == ':parsepoint':
            self.show_parsepoint = not self.show_parsepoint
        elif self.allow_special_commands and line == ':trace':
            self.interpereter.trace = not self.interpereter.trace
        elif self.allow_special_commands and line == ':type':
            self.show_result_type = not self.show_result_type
        elif self.allow_special_commands and line == ':dump':
            c = self.linker.constructed()
            for byte, elnk in zip(c.bytecode, c.error_link):
                print(byte, elnk)
        elif self.allow_special_commands and line == ':cache':
            for key, value in self.interpereter.calling_cache.values.items():
                prt('{:40} : {:20}'.format(str(key), str(value)))
        elif self.allow_special_commands and line == ':memory':
            mem = self.interpereter.get_memory_usage()
            print(mem // 1024, 'KB')
        elif self.allow_special_commands and line.startswith(':file '):
            # TODO: Flag to suppress this command?
            # TODO: This will interperet special commands.
            # Can recursively load files, which might be bad.
            fn = line.split()[1]
            code = open(fn).read()
            await self.execute_internal(code, **kwargs)
        else:
            try:
                worked = False
                tokens, ast = calculator.parser.parse(line, source_name = 'iterm_' + str(self.line_count))
                if self.show_tree:
                    prt(json.dumps(ast, indent = 4))
                ast = {'#': 'program', 'items': [ast, {'#': 'end'}]}
                self.interpereter.stack = [None]
                self.interpereter.place = self.linker.add_segment(
                    calculator.bytecode.ast_to_bytecode(ast)
                )
                # for index, byte in enumerate(bytes):
                #   print('{:3d} - {}'.format(index, byte))
                result_items = await asyncio.wait_for(self.interpereter.run_async(get_entire_stack = True), 5)
                details['result'] = result_items
                worked = True
                for result in result_items:
                    # Note: This is handled with a try / except because 
                    f_res = calculator.formatter.format(result, limit = self.output_limit)
                    try:
                        exact = result.evalf()
                        details['exact'] = exact
                        f_ext = calculator.formatter.format(exact, limit = self.output_limit)
                        f_ext = re.sub(r'\d+\.\d+', lambda x: x.group(0).rstrip('0').rstrip('.'), f_ext)
                        f_ext = calculator.formatter.sympy_cleanup(f_ext)
                        if f_ext in ['inf', '-inf', f_res]:
                            raise Exception
                        prt(f_res, '=', f_ext)
                    except Exception as e:
                        prt(f_res)
                    try:
                        details['latex'] = formatter.latex(result)
                    except Exception:
                        pass
                    if self.show_result_type:
                        prt(result.__class__)
                        prt(result.__class__.__mro__)
            except calculator.errors.CompilationError as e:
                prt('Compilation error')
                prt(e.description)
                if e.position is not None:
                    prt(format_error_place(line, e.position))
            except calculator.errors.EvaluationError as e:
                dbg = e._linking
                if dbg is None:
                    prt('No debugging information available for this error.')
                    # prt('You may wish to open an issue: github.com/DXsmiley/mathbot')
                else:
                    prt('Runtime error in', dbg['name'])
                    prt(format_error_place(dbg['code'], dbg['position']))
                prt(str(e))
                # prt('-' * len(str(e)), '\n')
            except calculator.parser.ParseFailed as e:
                prt('Parse error')
                prt(format_error_place(line, e.position))
            except calculator.parser.TokenizationFailed as e:
                prt('Tokenization error')
                prt(format_error_place(line, e.position))
            except calculator.errors.TooMuchOutputError:
                prt('Output was too large to display')
            except asyncio.TimeoutError:
                prt('Operation timed out')
            except Exception as e:
                traceback.print_exc()
                prt('Some other unknown error occurred')
        if not self.retain_cache:
            self.interpereter.clear_cache()
        return '\n'.join(output), worked, details


def handle_eval_error(prt, e):
    dbg = e._linking
    if dbg is None:
        prt('No debugging information available for this error.')
        # prt('You may wish to open an issue: github.com/DXsmiley/mathbot')
    else:
        prt('Runtime error in', dbg['name'])
        prt(format_error_place(dbg['code'], dbg['position']))
    prt(str(e))


def format_error_place(string, position):
    lines = [''] + string.split('\n') + ['']
    line = 1
    while line < len(lines) - 2 and position > len(lines[line]):
        position -= len(lines[line]) + 1
        line += 1
    tabs_to_the_left = lines[line][:position].count('\t')
    return ERROR_TEMPLATE.format(
        line_num = line,
        position = position + 1,
        prev = cleanup_line(lines[line - 1]),
        cur = cleanup_line(lines[line]),
        next = cleanup_line(lines[line + 1]),
        carat = ' ' * (position + tabs_to_the_left * (TAB_WITH - 1)) + '^'
    )


def cleanup_line(l):
    return l.replace('\t', ' ' * TAB_WITH)
