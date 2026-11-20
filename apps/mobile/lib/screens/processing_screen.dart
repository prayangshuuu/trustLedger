import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../design/theme.dart';
import '../router.dart';
import '../state/app_state.dart';
import '../widgets/common.dart';
import 'scaffold.dart';

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
    WidgetsBinding.instance.addPostFrameCallback((_) => _run());
  }

  Future<void> _run() async {
    setState(() => _error = null);
    final s = widget.state;
    final stepDelay = motion(context, TMotion.stepReveal);
    try {
      final result = await s.runApply();
      // Reveal the agent steps one by one so the user sees what happened
      for (final step in (result['trace'] as List).cast<Map<String, dynamic>>()) {
        await Future<void>.delayed(stepDelay);
        if (!mounted) return;
        setState(() => _done[step['node'] as String] = (step['ms'] as num).toDouble());
      }
      await Future<void>.delayed(stepDelay);
      if (!mounted) return;
      if (result['status'] == 'bhorsha_required') {
        context.pushReplacement(Routes.bhorsha);
      } else if (result['decision'] != null) {
        context.pushReplacement(Routes.score);
      } else {
        setState(() => _error = result['error'] ?? 'error');
      }
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
      listenable: s,
      builder: (context, _) => TLScaffold(
        state: s,
        title: s.t('processing'),
        body: ListView(
          padding: const EdgeInsets.all(TSpace.lg),
          children: [
            for (final step in pipelineSteps)
              ListTile(
                key: Key('step_$step'),
                leading: _done.containsKey(step)
                    ? const Icon(Icons.check_circle, color: TColor.good, semanticLabel: 'done')
                    : const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 2)),
                title: Text(s.t('step_$step')),
                trailing: _done.containsKey(step) ? Text('${_done[step]!.toStringAsFixed(0)} ms') : null,
              ),
            if (_error != null) ...[
              const SizedBox(height: TSpace.lg),
              FilledButton(onPressed: _run, child: Text(s.t('retry'))),
            ],
          ],
        ),
      ),
    );
  }
}
