// Generates lib/design/tokens.g.dart from ../design_tokens.json.
//   dart run tool/gen_tokens.dart          (run from apps/mobile)
//   dart run tool/gen_tokens.dart --check  (CI: fails if the generated file is stale)
import 'dart:convert';
import 'dart:io';

String colorLiteral(String hex) {
  var h = hex.replaceFirst('#', '').toUpperCase();
  if (h.length == 6) h = 'FF$h';
  return 'Color(0x$h)';
}

String camel(String a, String b) => '$a${b[0].toUpperCase()}${b.substring(1)}';

void main(List<String> args) {
  final tokens = jsonDecode(File('../design_tokens.json').readAsStringSync()) as Map<String, dynamic>;
  final out = StringBuffer()
    ..writeln('// GENERATED from apps/design_tokens.json by tool/gen_tokens.dart. Do not edit.')
    ..writeln('// ignore_for_file: constant_identifier_names')
    ..writeln("import 'package:flutter/painting.dart';")
    ..writeln()
    ..writeln('/// Colour tokens.')
    ..writeln('abstract final class TColor {');
  final color = tokens['color'] as Map<String, dynamic>;
  for (final group in color.entries) {
    for (final c in (group.value as Map<String, dynamic>).entries) {
      final name = group.key == 'brand' || group.key == 'status' ? c.key : camel(group.key, c.key);
      out.writeln('  static const $name = ${colorLiteral(c.value as String)};');
    }
  }
  out.writeln('}');

  final font = tokens['font'] as Map<String, dynamic>;
  out
    ..writeln()
    ..writeln('/// Font tokens.')
    ..writeln('abstract final class TFont {')
    ..writeln("  static const bangla = 'HindSiliguri';")
    ..writeln("  static const latinFallback = '${font['familyLatin']}';");
  for (final w in (font['weight'] as Map<String, dynamic>).entries) {
    out.writeln('  static const ${w.key} = FontWeight.w${w.value};');
  }
  out.writeln('}');

  void numbers(String cls, String doc, Map<String, dynamic> values, {String type = 'double'}) {
    out
      ..writeln()
      ..writeln('/// $doc')
      ..writeln('abstract final class $cls {');
    for (final v in values.entries) {
      if (v.value is Map) continue;
      final lit = type == 'double' ? (v.value as num).toDouble().toString() : '${v.value}';
      out.writeln('  static const $type ${v.key} = $lit;');
    }
    out.writeln('}');
  }

  numbers('TType', 'Type scale (logical pixels).', tokens['type'] as Map<String, dynamic>);
  numbers('TSpace', 'Spacing scale.', tokens['space'] as Map<String, dynamic>);
  numbers('TRadius', 'Corner radii.', tokens['radius'] as Map<String, dynamic>);
  final shadow = (tokens['shadow'] as Map<String, dynamic>)['card'] as Map<String, dynamic>;
  numbers('TShadow', 'Card shadow.', {'blur': shadow['blur'], 'y': shadow['y']});
  numbers('TMotion', 'Animation durations in milliseconds.', tokens['motion'] as Map<String, dynamic>, type: 'int');
  final layout = tokens['layout'] as Map<String, dynamic>;
  numbers('TLayout', 'Layout values.', {
    ...layout,
    'compactMax': (layout['breakpoints'] as Map)['compact'],
    'expandedMin': (layout['breakpoints'] as Map)['expanded'],
  });

  final target = File('lib/design/tokens.g.dart');
  final generated = out.toString();
  if (args.contains('--check')) {
    if (!target.existsSync() || target.readAsStringSync() != generated) {
      stderr.writeln('tokens.g.dart is stale: run `dart run tool/gen_tokens.dart`');
      exit(1);
    }
    stdout.writeln('tokens.g.dart is up to date');
    return;
  }
  target.writeAsStringSync(generated);
  stdout.writeln('wrote ${target.path}');
}
