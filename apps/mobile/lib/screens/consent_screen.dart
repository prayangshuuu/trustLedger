import 'package:flutter/material.dart';

import '../state/app_state.dart';
import '../widgets/common.dart';
import 'connect_data_screen.dart';
import 'processing_screen.dart';
import 'scaffold.dart';

const consentSources = ['sms', 'bills', 'recharge', 'ocr', 'bhorsha'];

class ConsentScreen extends StatefulWidget {
  const ConsentScreen({super.key, required this.state});

  final AppState state;

  @override
  State<ConsentScreen> createState() => _ConsentScreenState();
}

class _ConsentScreenState extends State<ConsentScreen> {
  late Set<String> _selected;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _selected = {...widget.state.consents};
  }

  Future<void> _continue() async {
    setState(() => _busy = true);
    final s = widget.state;
    try {
      await s.saveConsents(_selected);
      if (!mounted) return;
      final hasData = _selected.contains('sms') || _selected.contains('ocr') || _selected.contains('bills');
      await Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (_) => hasData ? ConnectDataScreen(state: s) : ProcessingScreen(state: s),
        ),
      );
    } catch (e) {
      if (mounted) showError(context, s, e, onRetry: _continue);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.state;
    return ListenableBuilder(
      listenable: widget.state,
      builder: (context, _) => TLScaffold(
        state: s,
        title: s.t('consent_title'),
        body: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(s.t('consent_intro'), style: const TextStyle(fontSize: 16)),
            const SizedBox(height: 12),
            for (final src in consentSources)
              Card(
                child: SwitchListTile(
                  key: Key('consent_$src'),
                  title: Text(s.t('src_$src'), style: const TextStyle(fontWeight: FontWeight.w600)),
                  subtitle: Text(s.t('src_${src}_d')),
                  value: _selected.contains(src),
                  onChanged: (on) => setState(() => on ? _selected.add(src) : _selected.remove(src)),
                ),
              ),
          ],
        ),
        bottom: FilledButton(
          key: const Key('consent_continue'),
          onPressed: _busy || _selected.isEmpty ? null : _continue,
          child: _busy ? const CircularProgressIndicator(color: Colors.white) : Text(s.t('continue')),
        ),
      ),
    );
  }
}
