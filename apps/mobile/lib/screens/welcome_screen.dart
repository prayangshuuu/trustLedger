import 'package:flutter/material.dart';

import '../state/app_state.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'consent_screen.dart';

class WelcomeScreen extends StatefulWidget {
  const WelcomeScreen({super.key, required this.state});

  final AppState state;

  @override
  State<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends State<WelcomeScreen> {
  late Future<List<dynamic>> _personas;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _personas = widget.state.api.personas();
  }

  Future<void> _pick(Map<String, dynamic> persona) async {
    setState(() => _busy = true);
    try {
      await widget.state.selectPersona(persona);
      if (!mounted) return;
      await Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => ConsentScreen(state: widget.state)));
    } catch (e) {
      if (mounted) showError(context, widget.state, e, onRetry: () => _pick(persona));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.state;
    return ListenableBuilder(
      listenable: s,
      builder: (context, _) => Scaffold(
        backgroundColor: TLColors.navy,
        body: SafeArea(
          child: ListView(
            padding: const EdgeInsets.all(24),
            children: [
              Align(
                alignment: Alignment.centerRight,
                child: LangToggle(state: s),
              ),
              const SizedBox(height: 24),
              const Icon(Icons.verified_user_rounded, color: TLColors.teal, size: 64),
              const SizedBox(height: 12),
              Text(
                s.t('app_name'),
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white, fontSize: 34, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              Text(
                s.t('tagline'),
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white70, fontSize: 16),
              ),
              const SizedBox(height: 32),
              Text(
                s.t('demo_mode'),
                style: const TextStyle(color: TLColors.gold, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 8),
              FutureBuilder<List<dynamic>>(
                future: _personas,
                builder: (context, snap) {
                  if (snap.hasError) {
                    return Column(
                      children: [
                        Text(s.t('err_network'), style: const TextStyle(color: Colors.white)),
                        TextButton(
                          onPressed: () => setState(() => _personas = s.api.personas()),
                          child: Text(s.t('retry')),
                        ),
                      ],
                    );
                  }
                  if (!snap.hasData) return const Center(child: CircularProgressIndicator());
                  return Column(
                    children: [
                      for (final p in snap.data!.cast<Map<String, dynamic>>())
                        Card(
                          child: ListTile(
                            key: Key('persona_${p['key']}'),
                            leading: const WalletIcon(),
                            title: Text(
                              _personaName(p['key'] as String, s.lang),
                              style: const TextStyle(fontWeight: FontWeight.w600),
                            ),
                            subtitle: Text(p['description'] as String),
                            trailing: _busy ? null : const Icon(Icons.arrow_forward),
                            onTap: _busy ? null : () => _pick(p),
                          ),
                        ),
                    ],
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}

String _personaName(String key, String lang) => switch ((key, lang)) {
  ('shathi', 'bn') => 'শাথী — পোশাক শ্রমিক',
  ('student', 'bn') => 'রাফি — ছাত্র ও ফ্রিল্যান্সার',
  ('homemaker', 'bn') => 'রিনা — গৃহিণী (ভরসা সম্পন্ন)',
  ('newcomer', 'bn') => 'মিতু — নতুন (কোনো ইতিহাস নেই)',
  ('shathi', _) => 'Shathi — garment worker',
  ('student', _) => 'Rafi — student and freelancer',
  ('homemaker', _) => 'Rina — homemaker (Bhorsha done)',
  _ => 'Mitu — newcomer (no history)',
};
