if __name__ != '__main__':
    
    print('Not main process. Probably crucible?')

else:
    
    print('Main process starting up')

    import sys
    import json
    import re
    import bot
    import utils
    import core.parameters

    @utils.apply(core.parameters.load_parameters, list)
    def retrieve_parameters():
        for i in sys.argv[1:]:
            if re.fullmatch(r'\w+\.env', i):
                with open(os.environ.get(i[:-4])) as f:
                    yield json.load(f)
            elif i.startswith('{') and i.endswith('}'):
                yield json.loads(i)
            else:
                with open(i) as f:
                    yield json.load(f)

    bot.run(retrieve_parameters())
 