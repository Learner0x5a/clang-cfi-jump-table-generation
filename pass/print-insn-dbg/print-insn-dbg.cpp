/*
 * 在输出函数IR的时候加上[源文件:行号]
 */
#include "llvm/Pass.h"
#include "llvm/IR/Value.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/Function.h"
#include "llvm/Support/raw_ostream.h"

#include "llvm/IR/DebugLoc.h"
#include "llvm/IR/DebugInfoMetadata.h"

#include <string>

using namespace llvm;


static void getDebugLoc(const Instruction *I, std::string &Dir, std::string &Filename, unsigned &Line) {
  if (DILocation *Loc = I->getDebugLoc()) {
    Line = Loc->getLine();
    Filename = Loc->getFilename().str();
    Dir = Loc->getDirectory().str();

    if (Filename.empty()) {
      DILocation *oDILoc = Loc->getInlinedAt();
      if (oDILoc) {
        Line = oDILoc->getLine();
        Filename = oDILoc->getFilename().str();
        Dir = oDILoc->getDirectory().str();
      }
    }
  }
}

namespace {
struct HelloWorld : public FunctionPass {
  static char ID;
  HelloWorld() : FunctionPass(ID) {}

  bool runOnFunction(Function &F) override {
    //Module *M = F.getParent();
    //outs()<< M->getModuleIdentifier()<<':';
    outs()<<"[function] ";
    outs().write_escaped(F.getName()) << '\n';
    outs()<<F<<'\n';
    outs()<<"[ins]\n";
    //errs()<<*(F.getFunctionType())<<'\n';
    //outs()<<*(F.getMetadata(LLVMContext::MD_type))<<'\n';
    for(auto &BB:F){
        unsigned curr_line = 0;
        std::string curr_filename = "";
        std::string curr_file_dir = "";
        static const std::string Xlibs("/usr/");
        for(auto &I:BB){
            getDebugLoc(&I, curr_file_dir, curr_filename, curr_line);
            if (curr_filename.empty() || curr_line == 0 || !curr_filename.compare(0, Xlibs.size(), Xlibs))
                continue;

            //outs()<<"[debug] Current instruction: "<<curr_filename<<":"<<curr_line<<"\n";
            outs()<<I<<"[debug] Current instruction: "<<curr_file_dir<<'/'<<curr_filename<<":"<<curr_line<<'\n';
        }

    }
    return false;
  }
}; // end of struct
}  // end of anonymous namespace

char HelloWorld::ID = 0;
static RegisterPass<HelloWorld> X("printINSdbg", "Print insn with src:line Pass");

