'''
Parsing llvm IR to generate jump tables for each function type
0. 解析opt pass生成的新IR，将icallsite_ir和所有callee都转为其[源文件:行号]
1. 为每个type生成一张表: 生成字典 {type:targets}
2. 解析icallsite指令，获取callee type: 生成字典 {icallsite_ir:targets}

Usage:
    python3 argv[0] path/to/target.ll path/to/target.ll.new <package-name>

Input:
    sys.argv[1] # ir by clang
    sys.argv[2] # ir after opt pass
    sys.argv[3] # package name, e.g. coreutils
Output:
    type2targets
    icallsite2targets
'''
import sys

# 获取type metadata，例如_ZTSFiiE
def getTypeMetadata(line):
    metadata_str = ''
    try:
        start = line.index('\"')
        end = line.index('\"',start+1)
        metadata_str = line[start+1:end]
    except:
        pass
    # print('[debug]', metadata_str)
    '''
    https://github.com/llvm/llvm-project/blob/master/llvm/tools/llvm-cxxdump/llvm-cxxdump.cpp
    '''
    if metadata_str.startswith('_ZT') or metadata_str.startswith('__ZT'):
        return metadata_str
    elif metadata_str.startswith('_CT') or metadata_str.startswith('__CT'):
        return metadata_str
    elif metadata_str.startswith('??_R0'):
        return metadata_str
    else:
        return ''

# 不知道为什么，过了一遍opt pass之后，ir的dbg metadata有时候标的不对，所以先去掉
def removeDebugMetadata(line):
    while '!dbg' in line:
        start = line.index('!dbg')
        try:
            end = line.index('!',line.index('!',start+1) + 1)
        except: # !dbg is the last metadata in this line
            end = len(line)-1
        line = line[:start] + line[end:]
    # print('[debug]',line)
    return line

# 解析opt pass ir
def parse_ir_new():
    funcDef2srcline = {}
    icallsiteIR2srcline = {}
    with open(sys.argv[2],'r',errors='ignore') as f:
        lines = f.readlines()
        # print('[debug] lines in target.ll.new:',len(lines))
        for i in range(len(lines)):
            line = lines[i]
            if line.startswith('[function]'):
                for j in range(i+1,len(lines)): # 记录函数definition
                    if lines[j].startswith('define '):
                        func_def = removeDebugMetadata(lines[j])
                    if lines[j].startswith('[ins]'): # 继续向下搜寻函数的src:line
                        src_line = lines[j+1].split('Current instruction: ')[-1].strip()
                        # src_line = src_line[src_line.index(sys.argv[3]):]
                        funcDef2srcline[func_def] = src_line
                        # print('[debug]',func_def,src_line)
                        break
            if '@llvm.type.test' in line and '[debug]' in line and 'call ' in line: # 记录icallsite_ir -> src:line
                icallsite_ir = removeDebugMetadata(line[0:line.index('[debug]')])
                src_line = line.split('Current instruction: ')[-1].strip()
                # src_line = src_line[src_line.index(sys.argv[3]):]
                # print('[debug]',icallsite_ir,src_line)
                icallsiteIR2srcline[icallsite_ir.strip()] = src_line

    return funcDef2srcline,icallsiteIR2srcline

# 解析clang ir
def parse_ir():
    # if not sys.argv[1] or not sys.argv[2]:
    try:
        sys.argv[1]
        sys.argv[2]
        sys.argv[3]
    except:
        print('Usage: python3 ',sys.argv[0],' /path/to/target.ll /path/to/target.ll.new <package-name>')
        print('Example: python3 ',sys.argv[0],' ./cp.ll ./cp.ll.new coreutils')
        exit(0)

    funcDef2srcline,icallsiteIR2srcline = parse_ir_new()

    typeid2targets = {}
    typeid2type = {}
    icallsite_type = []
    with open(sys.argv[1],'r') as f:
        for line in f:
            # print('[debug] len(line) in target.ll:',len(line))
            line = removeDebugMetadata(line)
            # 记录函数类型，形成typeid2targets字典
            if line.startswith('define ') and ('!type ' in line) and (not 'available_externally' in line): # 先不考虑外部函数，即以delcare开头/available_externally的行
                tokens = line.split()
                # print('[debug]',tokens)
                for idx in range(len(tokens)):
                    if tokens[idx] == '!type':
                        func_type = tokens[idx+1] # func_type是type metadata的id, e.g. !8
                        # 将ir对应到src_line
                        src_line = funcDef2srcline[line]
                        try:
                            typeid2targets[func_type].append(src_line) # target是一个字符串，即IR里面的function definition
                        except:
                            typeid2targets[func_type] = [src_line]
            # 记录typeid和type string的对应关系
            if line.startswith('!'):
                type_str = getTypeMetadata(line)
                if type_str:
                    tokens = line.split()
                    typeid = tokens[0]
                    typeid2type[typeid] = type_str
            # 记录icallsite，获取callee类型
            if '@llvm.type.test' in line and 'call ' in line:
                try:
                    tokens = line.split()
                    callee_type_idx = tokens.index('metadata') + 1
                    raw_callee_type = tokens[callee_type_idx]
                    start = raw_callee_type.index('\"')
                    end = raw_callee_type.index('\"',start+1)
                    callee_type = raw_callee_type[start+1:end] # type string, e.g. _ZTSFiiE
                    # print('[debug]',callee_type,' IN ',line)
                    # 将ir对应到src_line
                    src_line = icallsiteIR2srcline[line.strip()]
                    icallsite_type.append([src_line,callee_type])
                except:
                    print('callee type parsing error: metadata not found!')

    # 第一张表，type2targets
    type2targets = {}
    for key in typeid2targets:
        # print('[debug]',key,typeid2type[key],typeid2targets[key])
        type2targets[typeid2type[key]] = typeid2targets[key]

    # 第二张表，icallsite2targets
    icallsite2targets = {}
    for src_line,callee_type in icallsite_type:
        try:
            print('[*]',src_line,callee_type,type2targets[callee_type])
            icallsite2targets[src_line] = type2targets[callee_type]
        except:
            print('\n\t$$$$@@@@ llvm ir generation bug. non-existing callee type ',callee_type,'in metadata. @@@@$$$$\n')
    return type2targets,icallsite2targets


parse_ir()




