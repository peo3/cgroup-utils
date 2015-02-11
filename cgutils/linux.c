/*
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Library General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
 *
 * See the COPYING file for license information.
 *
 * Copyright (c) 2011 peo3 <peo314159265@gmail.com>
 */

/*
 * Usage in python:
 *
 *   import linux
 *   efd = linux.eventfd(0, 0)
 *   ...
 *   ret = struct.unpack('Q', os.read(efd, 8))
 *   ...
 *   linux.close(efd)
 */
#include <Python.h>
#include <unistd.h>
#include <sys/eventfd.h>

// For older glibc-headers
#ifndef EFD_SEMAPHORE
# define EFD_SEMAPHORE 1
# define EFD_CLOEXEC 02000000
# define EFD_NONBLOCK 04000
#endif

struct module_state {
    PyObject *error;
};

#if PY_MAJOR_VERSION >= 3
#define GETSTATE(m) ((struct module_state*)PyModule_GetState(m))
#endif

static PyObject *
linux_eventfd(PyObject *self, PyObject *args)
{
	int efd, initval, flags;

	if (!PyArg_ParseTuple(args, "ii", &initval, &flags))
		return NULL;
	efd = eventfd(initval, flags);
        if (efd == -1) {
                return PyErr_SetFromErrno(PyExc_OSError);
        } else {
	        return Py_BuildValue("i", efd);
        }
}

static PyObject *
linux_close(PyObject *self, PyObject *args)
{
	int ret, fd;

	if (!PyArg_ParseTuple(args, "i", &fd))
		return NULL;
	ret = close(fd);
        if (ret == -1) {
                return PyErr_SetFromErrno(PyExc_OSError);
        } else {
	        return Py_BuildValue("i", ret);
        }
}

static PyMethodDef LinuxSyscalls[] = {
	{"eventfd", (PyCFunction)linux_eventfd, METH_VARARGS,
		"Execute eventfd syscall."},
	{"close", (PyCFunction)linux_close, METH_VARARGS,
		"Execute close syscall."},
	{NULL, NULL, 0, NULL}
};

#if PY_MAJOR_VERSION >= 3
static int LinuxSyscalls_traverse(PyObject *m, visitproc visit, void *arg) {
	Py_VISIT(GETSTATE(m)->error);
	return 0;
}

static int LinuxSyscalls_clear(PyObject *m) {
	Py_CLEAR(GETSTATE(m)->error);
	return 0;
}

static struct PyModuleDef moduledef = {
        PyModuleDef_HEAD_INIT,
        "cgutils.linux",
        NULL,
        sizeof(struct module_state),
        LinuxSyscalls,
        NULL,
        LinuxSyscalls_traverse,
        LinuxSyscalls_clear,
        NULL
};
#endif

#if PY_MAJOR_VERSION >= 3
PyObject *
#else
PyMODINIT_FUNC
#endif
initlinux(void)
{
	PyObject *module, *dict;
	PyObject *val;

#if PY_MAJOR_VERSION >= 3
	module = PyModule_Create(&moduledef);
#else
	module = Py_InitModule("cgutils.linux", LinuxSyscalls);
#endif

	dict   = PyModule_GetDict(module);

	val = Py_BuildValue("i", EFD_CLOEXEC);
	PyDict_SetItemString(dict, "EFD_CLOEXEC", val);
	Py_DECREF(val);
	val = Py_BuildValue("i", EFD_NONBLOCK);
	PyDict_SetItemString(dict, "EFD_NONBLOCK", val);
	Py_DECREF(val);
	val = Py_BuildValue("i", EFD_SEMAPHORE);
	PyDict_SetItemString(dict, "EFD_SEMAPHORE", val);
	Py_DECREF(val);

#if PY_MAJOR_VERSION >= 3
	return module;
#endif
}

