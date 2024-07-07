from collections import defaultdict
from typing import Any, Dict, Optional, TypeVar, Generic, List, Union
import time
import random

T = TypeVar('T')

class Stack(Generic[T]):
    def __init__(self, head: T):
        self._stack: Dict[int, Optional[T]] = defaultdict(lambda: None)
        self._stack[0] = head
        self._ptr: int = 1
        self._size: int = 1

    def push(self, el: T) -> None:
        self._stack[self._ptr] = el
        self._ptr += 1
        self._size += 1

    def pop(self) -> Optional[T]:
        if self._ptr > 0:
            self._ptr -= 1
            el = self._stack[self._ptr]
            self._stack[self._ptr] = None
            self._size -= 1
            return el
        else:
            print("Stack is empty")
            return None

    def peek(self) -> Optional[T]:
        if self._ptr > 0:
            return self._stack[self._ptr - 1]
        else:
            print("Stack is empty")
            return None

    def is_empty(self) -> bool:
        return self._size == 0

class Process(Stack[str]):
    _pid_counter: int = 1

    def __init__(self, head: str):
        super().__init__(head)
        self._pid: int = Process._pid_counter
        Process._pid_counter += 1

    @property
    def pid(self) -> int:
        return self._pid

class Memory:
    def __init__(self):
        self._memory: Dict[int, Any] = {}

    def allocate(self, address: int, value: Any) -> None:
        self._memory[address] = value

    def deallocate(self, address: int) -> None:
        if address in self._memory:
            del self._memory[address]
        else:
            print(f"Memory address {address} is already empty.")

    def read(self, address: int) -> Optional[Any]:
        return self._memory.get(address)

    def write(self, address: int, value: Any) -> None:
        self._memory[address] = value

class Scheduler:
    def __init__(self, algorithm: str = "FCFS"):
        self._ready_queue: List[Process] = []
        self._algorithm = algorithm

    def add_process(self, process: Process) -> None:
        self._ready_queue.append(process)
        print(f"Process {process.pid} added to the scheduler.")

    def remove_process(self, pid: int) -> None:
        self._ready_queue = [process for process in self._ready_queue if process.pid != pid]
        print(f"Process {pid} removed from the scheduler.")

    def next_process(self) -> Optional[Process]:
        if self._ready_queue:
            if self._algorithm == "FCFS":
                return self._ready_queue.pop(0)
            elif self._algorithm == "SJF":
                self._ready_queue.sort(key=lambda p: p._size)
                return self._ready_queue.pop(0)
            elif self._algorithm == "RR":
                return self._ready_queue.pop(0)
            else:
                print("Unknown scheduling algorithm.")
                return None
        else:
            print("No more processes in the scheduler.")
            return None

class MemoryManager:
    def __init__(self, memory: Memory):
        self._memory = memory

    def allocate_memory(self, address: int, value: Any) -> None:
        self._memory.allocate(address, value)

    def deallocate_memory(self, address: int) -> None:
        self._memory.deallocate(address)

    def read_memory(self, address: int) -> Optional[Any]:
        return self._memory.read(address)

    def write_memory(self, address: int, value: Any) -> None:
        self._memory.write(address, value)

class CPU:
    def __init__(self, scheduler: Scheduler, memory_manager: MemoryManager, system):
        self._scheduler = scheduler
        self._memory_manager = memory_manager
        self._system = system
        self._registers = {
            'rax': 0, 'rbx': 0, 'rcx': 0, 'rdx': 0,
            'rsi': 0, 'rdi': 0, 'rbp': 0, 'rsp': 0x7FFFFFFFFFFF,
            'r8': 0, 'r9': 0, 'r10': 0, 'r11': 0,
            'r12': 0, 'r13': 0, 'r14': 0, 'r15': 0
        }
        self._flags = {'CF': 0, 'ZF': 0, 'SF': 0, 'OF': 0}
        self._pc = 0

    def fetch(self) -> Optional[str]:
        instruction = self._memory_manager.read_memory(self._pc)
        self._pc += 1
        return instruction

    def decode(self, instruction: str) -> bool:
        parts = instruction.split()
        opcode = parts[0].lower()

        if opcode == 'mov':
            dest, src = parts[1].split(',')
            if src.startswith('[') and src.endswith(']'):
                
                addr = self._registers[src[1:-1]]
                self._registers[dest] = self._memory_manager.read_memory(addr)
            elif dest.startswith('[') and dest.endswith(']'):
                
                addr = self._registers[dest[1:-1]]
                if src in self._registers:
                    value = self._registers[src]
                elif src.startswith('0x'):
                    value = int(src, 16)
                else:
                    value = int(src)
                self._memory_manager.write_memory(addr, value)
            elif src.startswith('0x'):
                self._registers[dest] = int(src, 16)
            elif src in self._registers:
                self._registers[dest] = self._registers[src]
            else:
                self._registers[dest] = int(src)

        elif opcode in ['add', 'sub', 'and', 'or', 'xor']:
            dest, src = parts[1].split(',')
            if src.startswith('0x'):
                value = int(src, 16)
            elif src in self._registers:
                value = self._registers[src]
            else:
                value = int(src)

            if opcode == 'add':
                result = self._registers[dest] + value
            elif opcode == 'sub':
                result = self._registers[dest] - value
            elif opcode == 'and':
                result = self._registers[dest] & value
            elif opcode == 'or':
                result = self._registers[dest] | value
            elif opcode == 'xor':
                result = self._registers[dest] ^ value

            self._registers[dest] = result & 0xFFFFFFFFFFFFFFFF  
            self._update_flags(result)

        elif opcode in ['inc', 'dec']:
            reg = parts[1]
            if opcode == 'inc':
                self._registers[reg] += 1
            else:
                self._registers[reg] -= 1
            self._registers[reg] &= 0xFFFFFFFFFFFFFFFF  
            self._update_flags(self._registers[reg])

        elif opcode == 'push':
            src = parts[1]
            self._registers['rsp'] -= 8
            if src in self._registers:
                value = self._registers[src]
            elif src.startswith('0x'):
                value = int(src, 16)
            else:
                value = int(src)
            self._memory_manager.write_memory(self._registers['rsp'], value)

        elif opcode == 'pop':
            dest = parts[1]
            value = self._memory_manager.read_memory(self._registers['rsp'])
            self._registers[dest] = value
            self._registers['rsp'] += 8

        elif opcode in ['jmp', 'je', 'jne', 'jg', 'jl', 'jge', 'jle']:
            target = parts[1]
            should_jump = False
            if opcode == 'jmp':
                should_jump = True
            elif opcode == 'je' and self._flags['ZF']:
                should_jump = True
            elif opcode == 'jne' and not self._flags['ZF']:
                should_jump = True
            elif opcode == 'jg' and not self._flags['ZF'] and self._flags['SF'] == self._flags['OF']:
                should_jump = True
            elif opcode == 'jl' and self._flags['SF'] != self._flags['OF']:
                should_jump = True
            elif opcode == 'jge' and self._flags['SF'] == self._flags['OF']:
                should_jump = True
            elif opcode == 'jle' and (self._flags['ZF'] or self._flags['SF'] != self._flags['OF']):
                should_jump = True

            if should_jump:
                if target.startswith('0x'):
                    self._pc = int(target, 16)
                else:
                    self._pc = int(target)

        elif opcode == 'cmp':
            left, right = parts[1].split(',')
            left_val = self._registers[left]
            if right in self._registers:
                right_val = self._registers[right]
            elif right.startswith('0x'):
                right_val = int(right, 16)
            else:
                right_val = int(right)
            result = left_val - right_val
            self._update_flags(result)

        elif opcode == 'call':
            self._registers['rsp'] -= 8
            self._memory_manager.write_memory(self._registers['rsp'], self._pc)
            self._pc = int(parts[1])

        elif opcode == 'ret':
            self._pc = self._memory_manager.read_memory(self._registers['rsp'])
            self._registers['rsp'] += 8

        elif opcode == 'hlt':
            return False

        return True

    def _update_flags(self, result):
        self._flags['ZF'] = int(result == 0)
        self._flags['SF'] = int(result < 0)
        self._flags['CF'] = int((result & 0x10000000000000000) != 0)  
        # Overflow flag здесь нужен

    def execute(self) -> bool:
        process = self._scheduler.next_process()
        if process:
            print(f"Executing process {process.pid}")
            instruction = self.fetch()
            if instruction:
                should_continue = self.decode(instruction)
                if self._pc == 80:  # System call for putchar
                    self._system.putchar(self._registers['rdi'])
                    self._pc += 1
                    return True
                print(f"Registers: {self._registers}")
                print(f"Flags: {self._flags}")
                return should_continue
        return False

class FileSystem:
    def __init__(self):
        self._files: Dict[str, str] = {}

    def create_file(self, filename: str, content: str) -> None:
        if filename in self._files:
            print(f"File {filename} already exists.")
        else:
            self._files[filename] = content
            print(f"File {filename} created.")

    def read_file(self, filename: str) -> Optional[str]:
        if filename in self._files:
            return self._files[filename]
        else:
            print(f"File {filename} not found.")
            return None

    def write_file(self, filename: str, content: str) -> None:
        if filename in self._files:
            self._files[filename] = content
            print(f"File {filename} updated.")
        else:
            print(f"File {filename} not found.")

    def delete_file(self, filename: str) -> None:
        if filename in self._files:
            del self._files[filename]
            print(f"File {filename} deleted.")
        else:
            print(f"File {filename} not found.")

class Logger:
    def __init__(self):
        self._logs: List[str] = []

    def log(self, message: str) -> None:
        self._logs.append(message)
        print(f"Log: {message}")

    def get_logs(self) -> List[str]:
        return self._logs

class ProcessManager:
    def __init__(self, scheduler: Scheduler):
        self._scheduler = scheduler

    def create_process(self, head: str) -> Process:
        process = Process(head)
        return process

    def terminate_process(self, pid: int) -> None:
        self._scheduler.remove_process(pid)

class SystemClock:
    def __init__(self):
        self._start_time = time.time()

    def get_time(self) -> float:
        return time.time() - self._start_time

class System:
    def __init__(self):
        self._memory = Memory()
        self._memory_manager = MemoryManager(self._memory)
        self._scheduler = Scheduler(algorithm="FCFS")
        self._file_system = FileSystem()
        self._logger = Logger()
        self._process_manager = ProcessManager(self._scheduler)
        self._system_clock = SystemClock()
        self._cpu = CPU(self._scheduler, self._memory_manager, self)

    def initialize_memory(self):
        
        for i in range(0x7FFFFFFFFFFF, 0x7FFFFFFFFFFF - 1024, -1):
            self._memory.allocate(i, 0)

    def add_process(self, process: Process) -> None:
        self._scheduler.add_process(process)

    def run(self) -> None:
        while self._memory.read(self._cpu._pc) is not None:
            if not self._cpu.execute():
                break

    def create_file(self, filename: str, content: str) -> None:
        self._file_system.create_file(filename, content)

    def read_file(self, filename: str) -> Optional[str]:
        return self._file_system.read_file(filename)

    def write_file(self, filename: str, content: str) -> None:
        self._file_system.write_file(filename, content)

    def delete_file(self, filename: str) -> None:
        self._file_system.delete_file(filename)

    def log(self, message: str) -> None:
        self._logger.log(message)

    def get_logs(self) -> List[str]:
        return self._logger.get_logs()

    def create_process(self, head: str) -> Process:
        return self._process_manager.create_process(head)

    def terminate_process(self, pid: int) -> None:
        self._process_manager.terminate_process(pid)

    def get_system_time(self) -> float:
        return self._system_clock.get_time()

    def putchar(self, char: int):
        print(chr(char), end='')

    def load_program(self, program: List[str]) -> None:
        for i, instruction in enumerate(program):
            self._memory.allocate(i, instruction)

if __name__ == "__main__":
    system = System()
    system.initialize_memory()

    program = [
        "mov rdi,0x100",  # Address to store the string
        "mov al,72",      # 'H'
        "mov [rdi],al",
        "inc rdi",
        "mov al,101",     # 'e'
        "mov [rdi],al",
        "inc rdi",
        "mov al,108",     # 'l'
        "mov [rdi],al",
        "inc rdi",
        "mov al,108",     # 'l'
        "mov [rdi],al",
        "inc rdi",
        "mov al,111",     # 'o'
        "mov [rdi],al",
        "inc rdi",
        "mov al,44",      # ','
        "mov [rdi],al",
        "inc rdi",
        "mov al,32",      # ' '
        "mov [rdi],al",
        "inc rdi",
        "mov al,87",      # 'W'
        "mov [rdi],al",
        "inc rdi",
        "mov al,111",     # 'o'
        "mov [rdi],al",
        "inc rdi",
        "mov al,114",     # 'r'
        "mov [rdi],al",
        "inc rdi",
        "mov al,108",     # 'l'
        "mov [rdi],al",
        "inc rdi",
        "mov al,100",     # 'd'
        "mov [rdi],al",
        "inc rdi",
        "mov al,33",      # '!'
        "mov [rdi],al",
        "inc rdi",
        "mov al,0",       # Null terminator
        "mov [rdi],al",
        "mov rsi,0x100",  # Address of the string
        "mov rdx,13",     # Length of the string
        "call 50",        # Call our print function
        "hlt",            # Halt the program
        
        "mov rcx,0",      
        "mov rdi,rsi",    
        "mov al,[rdi]",   
        "cmp al,0",       
        "je 65",          
        "push rax",       
        "call 70",        
        "pop rax",        
        "inc rdi",        
        "inc rcx",        
        "cmp rcx,rdx",    
        "jl 52",          
        "ret",            
        "push rdi",       
        "mov rdi,rax",    
        "call 80",        
        "pop rdi",        
        "ret",
        "hlt",
    ]

    process = system.create_process("hello_world")
    system.add_process(process)  
    system.load_program(program)
    system.run()

    system.log("System started and finished.")
    print(system.get_logs())
    print(f"System time: {system.get_system_time()} seconds")
