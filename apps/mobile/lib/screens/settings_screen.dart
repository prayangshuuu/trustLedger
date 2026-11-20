import 'package:flutter/material.dart';

import '../state/app_state.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'consent_screen.dart' show consentSources;

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key, required this.state});

  final AppState state;

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  bool _busy = false;

  Future<void> _toggle(String source, bool on) async {
    final s = widget.state;
    setState(() => _busy = true);
    try {
      if (on) {
        await s.api.grantConsent(s.userId!, source);
      } else {
        await s.api.revokeConsent(source);
      }
      await s.refreshProfile();
    } catch (e) {
      if (mounted) showError(context, s, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _delete() async {
    final s = widget.state;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        content: Text(s.t('delete_confirm')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(s.t('cancel'))),
          FilledButton(
            key: const Key('confirm_delete'),
            style: FilledButton.styleFrom(backgroundColor: TLColors.bad, minimumSize: const Size(0, 44)),
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(s.t('confirm')),
          ),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await s.deleteAll();
      if (!mounted) return;
      final messenger = ScaffoldMessenger.of(context);
      Navigator.of(context).popUntil((r) => r.isFirst);
      messenger.showSnackBar(SnackBar(content: Text(s.t('deleted'))));
    } catch (e) {
      if (mounted) showError(context, s, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.state;
    return ListenableBuilder(
      listenable: s,
      builder: (context, _) => Scaffold(
        appBar: AppBar(
          title: Text(s.t('settings')),
          actions: [LangToggle(state: s)],
        ),
        body: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(s.t('active_consents'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
            for (final src in consentSources)
              SwitchListTile(
                key: Key('settings_consent_$src'),
                title: Text(s.t('src_$src')),
                value: s.consents.contains(src),
                onChanged: _busy || s.userId == null ? null : (on) => _toggle(src, on),
              ),
            const Divider(height: 32),
            OutlinedButton.icon(
              key: const Key('delete_data'),
              style: OutlinedButton.styleFrom(foregroundColor: TLColors.bad, minimumSize: const Size.fromHeight(52)),
              icon: const Icon(Icons.delete_forever),
              label: Text(s.t('delete_data')),
              onPressed: s.userId == null ? null : _delete,
            ),
          ],
        ),
      ),
    );
  }
}
