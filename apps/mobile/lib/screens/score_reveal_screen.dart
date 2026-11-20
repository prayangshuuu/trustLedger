import 'package:flutter/material.dart';

import '../state/app_state.dart';
import '../theme.dart';
import '../widgets/score_meter.dart';
import 'reasons_screen.dart';
import 'scaffold.dart';

class ScoreRevealScreen extends StatelessWidget {
  const ScoreRevealScreen({super.key, required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final d = state.decision!;
    final band = d['band'] as String;
    return ListenableBuilder(
      listenable: state,
      builder: (context, _) => TLScaffold(
        state: state,
        title: state.t('your_score'),
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              KeyedSubtree(
                key: const Key('band_chip'),
                child: ScoreMeter(score: d['score'] as int, label: state.t('band_$band'), color: bandColor(band)),
              ),
              const SizedBox(height: 8),
              const Text('300 — 900', style: TextStyle(color: Colors.black54)),
            ],
          ),
        ),
        bottom: FilledButton(
          key: const Key('see_reasons'),
          onPressed: () =>
              Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => ReasonsScreen(state: state))),
          child: Text(state.t('why')),
        ),
      ),
    );
  }
}
