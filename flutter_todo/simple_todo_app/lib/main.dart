import 'package:flutter/material.dart';

void main() {
  runApp(const TodoApp());
}

class TodoApp extends StatelessWidget {
  const TodoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Flutter Todo App',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      home: const TodoListScreen(),
    );
  }
}

class Todo {
  final String id;
  final String task;
  bool isDone;

  Todo({
    required this.id,
    required this.task,
    this.isDone = false,
  });
}

class TodoListScreen extends StatefulWidget {
  const TodoListScreen({super.key});

  @override
  State<TodoListScreen> createState() => _TodoListScreenState();
}

class _TodoListScreenState extends State<TodoListScreen> {
  final List<Todo> _todos = [];
  final TextEditingController _textController = TextEditingController();

  void _addTodo() {
    final task = _textController.text.trim();
    if (task.isNotEmpty) {
      setState(() {
        _todos.add(Todo(
          id: DateTime.now().toString(),
          task: task,
        ));
        _textController.clear();
      });
    }
  }

  void _toggleTodo(String id) {
    setState(() {
      final todo = _todos.firstWhere((t) => t.id == id);
      todo.isDone = !todo.isDone;
    });
  }

  void _removeTodo(String id) {
    setState(() {
      _todos.removeWhere((t) => t.id == id);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Todo List'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: ListView.builder(
        itemCount: _todos.length,
        itemBuilder: (context, index) {
          final todo = _todos[index];
          return ListTile(
            title: Text(
              todo.task,
              style: TextStyle(
                decoration: todo.isDone ? TextDecoration.lineThrough : null,
              ),
            ),
            leading: Checkbox(
              value: todo.isDone,
              onChanged: (_) => _toggleTodo(todo.id),
            ),
            trailing: IconButton(
              icon: const Icon(Icons.delete),
              onPressed: () => _removeTodo(todo.id),
            ),
          );
        },
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _addTodo,
        tooltip: 'Add Todo',
        child: const Icon(Icons.add),
      ),
      bottomNavigationBar: Padding(
        padding: const EdgeInsets.all(8.0),
        child: TextField(
          controller: _textController,
          decoration: InputDecoration(
            hintText: 'Enter todo task...',
            suffixIcon: IconButton(
              icon: const Icon(Icons.send),
              onPressed: _addTodo,
            ),
            border: OutlineInputBorder(),
          ),
        ),
      ),
    );
  }
}
