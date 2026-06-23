set -e

cd /home/zzn/SASE/klee
# rm -rf build
# mkdir build
cd build
cmake -DCMAKE_BUILD_TYPE=Debug -DENABLE_SOLVER_STP=ON -DSTP_DIR=/home/ghq/globals/utils/stp/build -DENABLE_POSIX_RUNTIME=ON -DKLEE_UCLIBC_PATH=/home/ghq/globals/libs/klee-uclibc -DLLVM_CONFIG_BINARY=/home/ghq/globals/utils/llvms/llvm-13.0.1/build/bin/llvm-config ..
make -j32
echo "KLEE build done."
