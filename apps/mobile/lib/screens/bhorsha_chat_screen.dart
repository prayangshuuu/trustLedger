import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../router.dart';
import '../state/app_state.dart';
import '../design/theme.dart';
import '../widgets/common.dart';
import 'scaffold.dart';

class _Msg {
  _Msg(this.text, {required this.fromUser});

  final String text;
  final bool fromUser;
}

class BhorshaChatScreen extends StatefulWidget {
  const BhorshaChatScreen({super.key, required this.state});

  final AppState state;

  @override
  State<BhorshaChatScreen> createState() => _BhorshaChatScreenState();
}

class _BhorshaChatScreenState extends State<BhorshaChatScreen> {
  final _messages = <_Msg>[];
  final _input = TextEditingController();
  final _inputFocus = FocusNode();
  final _scroll = ScrollController();
  String? _sessionId;
  bool _busy = true;
  bool _completed = false;
  int _turn = 0;
  int _total = 12;
  DateTime _askedAt = DateTime.now();

  @override
  void initState() {
    super.initState();
    _start();
  }

  @override
  void dispose() {
    _input.dispose();
    _inputFocus.dispose();
    _scroll.dispose();
    super.dispose();
  }

  void _addBot(String text) => _messages.add(_Msg(text, fromUser: false));

  Future<void> _start() async {
    final s = widget.state;
    try {
      if (!s.consents.contains('bhorsha')) {
        await s.api.grantConsent(s.userId!, 'bhorsha');
        await s.refreshProfile();
      }
      final q = await s.api.bhorshaStart(s.userId!);
      setState(() {
        _sessionId = q['session_id'] as String;
        _turn = q['turn'] as int;
        _total = q['total_turns'] as int;
        _addBot(s.t('bhorsha_intro'));
        _addBot(s.lang == 'bn' ? q['question_text'] as String : q['english_translation'] as String);
        _askedAt = DateTime.now();
        _busy = false;
      });
    } catch (e) {
      if (mounted) showError(context, s, e, onRetry: _start);
    }
  }

  Future<void> _send() async {
    final s = widget.state;
    final text = _input.text.trim();
    if (text.isEmpty || _sessionId == null) return;
    final elapsed = DateTime.now().difference(_askedAt).inMilliseconds / 1000;
    setState(() {
      _messages.add(_Msg(text, fromUser: true));
      _input.clear();
      _busy = true;
    });
    try {
      final r = await s.api.bhorshaAnswer(_sessionId!, text, elapsed);
      setState(() {
        if (r['acknowledgement'] != null) _addBot(r['acknowledgement'] as String);
        if (r['completed'] == true) {
          _completed = true;
          _addBot((r['message'] as String?) ?? '');
        } else {
          _turn = r['turn'] as int;
          _addBot(s.lang == 'bn' ? r['question_text'] as String : r['english_translation'] as String);
          _askedAt = DateTime.now();
        }
        _busy = false;
      });
      await Future<void>.delayed(const Duration(milliseconds: 50));
      if (_scroll.hasClients) _scroll.jumpTo(_scroll.position.maxScrollExtent);
      // Keep the cursor in the answer box so the next answer can be typed straight away
      if (mounted && !_completed) _inputFocus.requestFocus();
    } catch (e) {
      setState(() => _busy = false);
      if (mounted) showError(context, s, e);
    }
  }

  Future<void> _finish() async {
    final s = widget.state;
    setState(() => _busy = true);
    try {
      await s.api.bhorshaResult(_sessionId!);
      if (!mounted) return;
      context.pushReplacement(Routes.processing);
    } catch (e) {
      setState(() => _busy = false);
      if (mounted) showError(context, s, e, onRetry: _finish);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.state;
    return ListenableBuilder(
      listenable: widget.state,
      builder: (context, _) => TLScaffold(
        state: s,
        title: '${s.t('bhorsha_title')} ($_turn/$_total)',
        body: Column(
          children: [
            LinearProgressIndicator(value: _total == 0 ? 0 : _turn / _total, color: TColor.tealDark),
            Expanded(
              child: ListView.builder(
                controller: _scroll,
                padding: const EdgeInsets.all(TSpace.md),
                itemCount: _messages.length,
                itemBuilder: (_, i) {
                  final m = _messages[i];
                  return Align(
                    alignment: m.fromUser ? Alignment.centerRight : Alignment.centerLeft,
                    child: Container(
                      margin: const EdgeInsets.symmetric(vertical: TSpace.xs),
                      padding: const EdgeInsets.all(TSpace.md),
                      constraints: const BoxConstraints(maxWidth: 320),
                      decoration: BoxDecoration(
                        color: m.fromUser ? TColor.tealDark : TColor.lightSurface,
                        borderRadius: BorderRadius.circular(TRadius.lg),
                        boxShadow: const [BoxShadow(color: TColor.lightShadow, blurRadius: TShadow.blur)],
                      ),
                      child: Text(
                        m.text,
                        style: TextStyle(color: m.fromUser ? TColor.lightSurface : TColor.navy, fontSize: TType.body),
                      ),
                    ),
                  );
                },
              ),
            ),
            if (_completed)
              Padding(
                padding: const EdgeInsets.all(TSpace.lg),
                child: FilledButton(
                  key: const Key('bhorsha_finish'),
                  onPressed: _busy ? null : _finish,
                  child: Text(s.t('bhorsha_done')),
                ),
              )
            else
              Padding(
                padding: const EdgeInsets.all(TSpace.sm),
                child: Row(
                  children: [
                    Expanded(
                      child: TextField(
                        key: const Key('bhorsha_input'),
                        controller: _input,
                        focusNode: _inputFocus,
                        autofocus: true,
                        textInputAction: TextInputAction.send,
                        onSubmitted: (_) => _busy ? null : _send(),
                        minLines: 1,
                        maxLines: 3,
                        decoration: InputDecoration(hintText: s.t('type_answer'), border: const OutlineInputBorder()),
                      ),
                    ),
                    IconButton(
                      key: const Key('bhorsha_send'),
                      icon: const Icon(Icons.send, color: TColor.tealDark),
                      tooltip: s.t('send'),
                      onPressed: _busy ? null : _send,
                    ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}
