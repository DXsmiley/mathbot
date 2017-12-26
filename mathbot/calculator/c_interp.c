/*

	Interpereter written in C, rather than Python.

	This is an *experimental* version of the interpereter.
	To use it, first compile it. Use gcc or whatever. No
	external libraries are needed. Note that some of the
	format strings (%I64d) might need to be modified for
	use with non-windows systems.

	Then gernate some bytecode:

		python -m calculator my_code_file -c > bytecode_file

	Then run the bytecode:

		c_interp bytecode_file

	This implementation is far behind the Python version
	of the interpereter.

*/

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>


typedef struct scope_t * Scope;
typedef struct datum_t Datum;
typedef struct interpereter_t * Interpereter;


#define TYPE_NONE 0
#define TYPE_INSTRUCTION 1
#define TYPE_INTEGER 2
#define TYPE_REAL 3
#define TYPE_FUNCTION 4
#define TYPE_LIST 5
#define TYPE_SCOPE 6


#define INST_NOTHING 0
#define INST_CONSTANT 1
#define INST_CONSTANT_EMPTY_ARRAY 50

#define INST_BIN_ADD 2
#define INST_BIN_SUB 3
#define INST_BIN_MUL 4
#define INST_BIN_DIV 5
#define INST_BIN_MOD 6
#define INST_BIN_POW 7
#define INST_BIN_AND 8
#define INST_BIN_OR  9

#define INST_UNR_NOT 11
#define INST_UNR_MIN 12
#define INST_UNR_FAC 13

#define INST_ASSIGNMENT 17

#define INST_END     19

#define INST_DECLARE_FUNCTION_MACRO 20
#define INST_DECLARE_FUNCTION 21
#define INST_RETURN 22

#define INST_JUMP          23
#define INST_JUMP_IF_TRUE  24
#define INST_JUMP_IF_FALSE 25
#define INST_JUMP_IF_MACRO 14

#define INST_TOP_DUPLICATE 26
#define INST_TOP_DISCARD   27

#define INST_ARG_LIST_END 15
#define INST_ARG_LIST_END_NO_CACHE 16
#define INST_ARG_LIST_END_TAIL_OP  17
#define INST_STORE_IN_CACHE        41


struct datum_t {

	unsigned char type;
	unsigned char gc_mark;

	union {

		long long int integer;

		double real;

		struct {
			unsigned int id;
			unsigned int line_number;
			char * filename;
		} instruction;

		struct {
			int address;
			Scope scope;
		} function;

		struct {
			Datum * item;
			Datum * next;
		} list;

		Scope scope;

	};

};


struct scope_t {

	Datum * elements;
	unsigned int size;
	Scope superscope;

};



struct interpereter_t {

	Datum * stack;
	int stack_size;
	Datum * instructions;
	int instruction_pointer;
	Scope global_scope;


};


Datum stackPop(Interpereter interp) {
	return interp -> stack[--interp -> stack_size];
}


void stackPush(Interpereter interp, Datum datum) {
	interp -> stack[interp -> stack_size++] = datum;
}


Datum next(Interpereter interp) {
	return interp -> instructions[++interp -> instruction_pointer];
}


long long int expectInteger(Datum datum) {
	assert(datum.type == TYPE_INTEGER);
	return datum.integer;
}


Datum createInteger(long long int value) {
	Datum d;
	d.type = TYPE_INTEGER;
	d.integer = value;
	return d;
}


Datum createReal(double value) {
	Datum d;
	d.type = TYPE_REAL;
	d.real = value;
	return d;
}


void binaryOperator(Interpereter interp, long long int (*fi)(long long int, long long int), double (*fr)(double, double)) {
	Datum right = stackPop(interp);
	Datum left = stackPop(interp);
	Datum result;
	if (left.type == TYPE_INTEGER) {
		if (right.type == TYPE_INTEGER) {
			result = createInteger(fi(left.integer, right.integer));
		} else if (right.type == TYPE_REAL) {
			result = createReal(fr(left.integer, right.real));
		} else {
			fprintf(stderr, "Incompatible types for addition\n");
			abort();
		}
	} else if (left.type == TYPE_REAL) {
		if (right.type == TYPE_INTEGER) {
			result = createReal(fr(left.real, right.integer));
		} else if (right.type == TYPE_REAL) {
			result = createReal(fr(left.real, right.real));
		} else {
			fprintf(stderr, "Incompatible types for addition\n");
			abort();
		}
	} else {
		fprintf(stderr, "Incompatible types for addition\n");
		abort();
	}
	stackPush(interp, result);
}


long long int binAddI(long long int l, long long int r) {return l + r;}
double        binAddR(       double l,        double r) {return l + r;}
long long int binSubI(long long int l, long long int r) {return l - r;}
double        binSubR(       double l,        double r) {return l - r;}
long long int binMulI(long long int l, long long int r) {return l * r;}
double        binMulR(       double l,        double r) {return l * r;}
// Make this always cast to a double???
long long int binDivI(long long int l, long long int r) {return l / r;}
double        binDivR(       double l,        double r) {return l / r;}
long long int binModI(long long int l, long long int r) {return l % r;}
// double        binModR(       double l,        double r) {return l % r;}


int tick(Interpereter interp) {
	Datum inst = next(interp);
	assert(inst.type == TYPE_INSTRUCTION);
	switch (inst.instruction.id) {

		case INST_CONSTANT:
			stackPush(interp, next(interp));
			break;
		
		case INST_END:
			return 0;
			break;

		case INST_BIN_ADD: binaryOperator(interp, binAddI, binAddR); break;
		case INST_BIN_SUB: binaryOperator(interp, binSubI, binSubR); break;
		case INST_BIN_MUL: binaryOperator(interp, binMulI, binMulR); break;
		case INST_BIN_DIV: binaryOperator(interp, binDivI, binDivR); break;
		
		case INST_ASSIGNMENT: {
			long long int address = expectInteger(next(interp));
			Datum value = stackPop(interp);
			printf("Assigning ");
			printDatum(value);
			printf(" to %d\n", address);
			// Do assignment
		} break;
		
		case INST_DECLARE_FUNCTION: {
			long long int address = expectInteger(next(interp));
			Datum function;
			function.type = TYPE_FUNCTION;
			function.function.address = address;
			// function.function.scope = ???;
			stackPush(interp, function);
		} break;
		
		default:
			fprintf(stderr, "Instruction %d not implemented.\n", inst.instruction.id);
	}
	return 1;
}


void printDatum(Datum datum) {
	switch (datum.type) {
		case TYPE_NONE:
			printf("none");
			break;
		case TYPE_INTEGER:
			printf("%I64d", datum.integer);
			break;
		case TYPE_REAL:
			printf("%lf", datum.real);
			break;
		case TYPE_INSTRUCTION:
			printf("[%u %u %s]", datum.instruction.id, datum.instruction.line_number, datum.instruction.filename);
			break;
		case TYPE_FUNCTION:
			printf("[function @%d]", datum.function.address);
			break;
		default:
			printf("[unknown datum]");
	}
}


Datum * loadInstructions(char * filename) {
	Datum * list = calloc(4096, sizeof(Datum));
	FILE * file = fopen(filename, "r");
	char type[32] = {'\0'};
	for (unsigned int place = 0;; ++place) {
		fscanf(file, " %s", type);
		// printf("%d %s\n", place, type);
		if (strcmp(type, "int") == 0) {
			Datum d;
			d.type = TYPE_INTEGER;
			fscanf(file, " %I64d", &d.integer);
			list[place] = d;
		} else if (strcmp(type, "flt") == 0) {
			Datum d;
			d.type = TYPE_REAL;
			fscanf(file, " %lf", &d.real);
			list[place] = d;			
		} else if (strcmp(type, "ist") == 0) {
			Datum d;
			d.type = TYPE_INSTRUCTION;
			d.instruction.filename = calloc(32, sizeof(char));
			fscanf(file, " %u %u %s",
				&d.instruction.id,
				&d.instruction.line_number,
				d.instruction.filename
			);
			list[place] = d;						
		} else if (strcmp(type, "str") == 0) {
			Datum d;
			d.type = TYPE_NONE;
			list[place] = d;
			// Read the thing so that other stuff doesn't become out of whack.
			char * string = malloc(128 * sizeof(char));
			fscanf(file, " %s", string);
		} else if (strcmp(type, "source") == 0) {
			break;
		} else {
			fprintf(stderr, "Unknown thingo in the bytecode file: %s\n", type);
			// abort();
			--place;
		}
	}
	fclose(file);
	return list;
}


int main(int argc, char ** argv) {
	if (argc != 2) {
		fprintf(stderr, "Usage: interp [filename]\n");
		return 0;
	}
	printf("Loading from %s...\n", argv[1]);
	Interpereter interp = malloc(sizeof(*interp));
	interp -> stack = calloc(4096, sizeof(Datum));
	interp -> stack_size = 0;
	interp -> instructions = loadInstructions(argv[1]);
	interp -> instruction_pointer = -1;
	printf("Running code...\n");
	while (tick(interp));
	for (int i = 0; i < interp -> stack_size; ++i) {
		printf("%3d | ", i);
		printDatum(interp -> stack[i]);
		printf("\n");
	}
	free(interp);
	return EXIT_SUCCESS;
}