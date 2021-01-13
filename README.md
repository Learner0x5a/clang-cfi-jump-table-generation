# clang-cfi jump table generation

Use [wllvm](https://github.com/travitch/whole-program-llvm) to build target packages.

Implement an LLVM pass to record the src:line of each instruction in IR.

Implement a python script to parse the after-opt IR and generate a jump table for each function type.

The python script additionally generate jump tables for indirect call sites.

Tested with clang-6.0 & llvm-6.0 on Ubuntu 18.04.

## Usage
```
# 0. build pass
git clone https://github.com/Learner0x5a/clang-cfi-jump-table-generation.git
cd pass
mkdir build
cd build
cmake ../
make

# 1. install wllvm
python3 -m pip install wllvm

# 2. build target package, e.g. coreutils-7.6
# 2.1 get patches for building old version coreutils on newer glibc machines
cd ~
git clone https://github.com/Learner0x5a/coreutils-patches.git

# 2.2 build
wget https://mirrors.aliyun.com/gnu/coreutils/coreutils-7.6.tar.gz
tar xvf coreutils-7.6.tar.gz
mv coreutils-7.6 coreutils-7.6-O3
cd coreutils-7.6-O3
patch -p1 < ~/patches_coreutils/patch-7.2-8.3
export LLVM_COMPILER=clang
# modify -B <dir> if necessary
export LLVM_BITCODE_GENERATION_FLAGS="-B clang-cfi-jump-table-generation/gold -flto -fsanitize=cfi-icall"
./configure CFLAGS="-g -O3"
make -j12

# 2.3 extract & disassemble target binary
cd src
extarct-bc ./cp
llvm-dis-6.0 cp.bc

# 3. run analysis 
opt-6.0 -load clang-cfi/pass/build/print-insn-dbg/libprint-insn-dbg.so -printINSdbg ./cp.ll > cp.ll.new
# python3 argv[0] path/to/target.ll path/to/target.ll.new <package-name>
python3 clang-cfi/parse_ir.py ./cp.ll ./cp.ll.new coreutils


```


