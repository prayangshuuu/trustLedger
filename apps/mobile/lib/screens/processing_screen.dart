import 'package:flutter/material.dart';

import '../state/app_state.dart';
import '../widgets/common.dart';
import 'bhorsha_chat_screen.dart';
import 'scaffold.dart';
import 'score_reveal_screen.dart';

const pipelineSteps = [
  'data_agent',
  'bhorsha_router',
  'scoring_agent',
  'explainer_agent',
  'fairness_agent',
  'finalize',
];

class ProcessingScreen extends StatefulWidget {
  const ProcessingScreen({super.key, required this.state});

  final AppState state;

  @override
  State<ProcessingScreen> createState() => _ProcessingScreenState();
}

class _ProcessingScreenState extends State<ProcessingScreen> {
  final Map<String, double> _done = {};
  Object? _error;

  @override
  void initState() {
    super.initState();
    _run();
  }

  Future<void> _run() async {
    setState(() => _error = null);
    final s = widget.state;
    try {
      final result = await s.runApply();
      // Reveal the agent steps one by one so the user sees what happened
      for (final step in (result['trace'] as List).cast<Map<String, dynamic>>()) {
        await Future<void>.delayed(const Duration(milliseconds: 350));
        if (!mounted) return;
        setState(() => _done[step['node'] as String] = (step['ms'] as num).toDouble());
      }
      await Future<void>.delayed(const Duration(milliseconds: 400));
      if (!mounted) return;
      final next = result['status'] == 'bhorsha_required'
          ? BhorshaChatScreen(state: s)
          : (result['decision'] == null ? null : ScoreRevealScreen(state: s));
      if (next == null) {
        setState(() => _error = result['error'] ?? 'error');
        return;
      }
      await Navigator.of(context).pushReplacement(MaterialPageRoute<void>(builder: (_) => next));
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e);
      showError(context, s, e, onRetry: _run);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.state;
    return ListenableBuilder(
      listenable: widget.state,
      builder: (context, _) => TLScaffold(
        state: s,
        title: s.t('processing'),
        body: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            for (final step in pipelineSteps)
              ListTile(
                key: Key('step_$step'),
                leading: _done.containsKey(step)
                    ? const Icon(Icons.check_circle, color: Colors.green)
                    : const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2)),
                title: Text(s.t('step_$step')),
                trailing: _done.containsKey(step) ? Text('${_done[step]!.toStringAsFixed(0)} ms') : null,
              ),
            if (_error != null) ...[
              const SizedBox(height: 16),
              FilledButton(onPressed: _run, child: Text(s.t('retry'))),
            ],
          ],
        ),
      ),
    );
  }
}
