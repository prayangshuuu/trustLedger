import 'package:flutter/material.dart';

import 'tokens.g.dart';

export 'tokens.g.dart';

/// Material theme generated from the design tokens (apps/design_tokens.json).
ThemeData buildTheme() {
  final scheme = ColorScheme.fromSeed(
    seedColor: TColor.teal,
    primary: TColor.tealDark,
    secondary: TColor.gold,
    surface: TColor.lightBackground,
    onPrimary: TColor.lightOnBrand,
  );
  const text = TextTheme(
    displaySmall: TextStyle(fontSize: TType.display, fontWeight: TFont.bold, color: TColor.navy),
    headlineMedium: TextStyle(fontSize: TType.headline, fontWeight: TFont.bold),
    titleLarge: TextStyle(fontSize: TType.title, fontWeight: TFont.bold),
    titleMedium: TextStyle(fontSize: TType.titleSmall, fontWeight: TFont.bold),
    bodyLarge: TextStyle(fontSize: TType.body),
    bodyMedium: TextStyle(fontSize: TType.bodySmall),
    labelSmall: TextStyle(fontSize: TType.caption),
  );
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    fontFamily: TFont.bangla,
    textTheme: text,
    scaffoldBackgroundColor: TColor.lightBackground,
    appBarTheme: const AppBarTheme(
      backgroundColor: TColor.navy,
      foregroundColor: TColor.lightOnBrand,
      centerTitle: false,
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: ButtonStyle(
        backgroundColor: WidgetStateProperty.all(TColor.tealDark),
        foregroundColor: WidgetStateProperty.all(TColor.lightOnBrand),
        minimumSize: WidgetStateProperty.all(const Size.fromHeight(TLayout.buttonHeight)),
        textStyle: WidgetStateProperty.all(
          const TextStyle(fontSize: TType.body + 1, fontWeight: TFont.semibold, fontFamily: TFont.bangla),
        ),
        side: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.focused)) {
            return const BorderSide(color: TColor.gold, width: 2.5);
          }
          return BorderSide.none;
        }),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: ButtonStyle(
        side: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.focused)) {
            return const BorderSide(color: TColor.gold, width: 2.5);
          }
          return const BorderSide(color: TColor.tealDark);
        }),
      ),
    ),
    // Visible keyboard focus on desktop and web
    focusColor: TColor.gold.withValues(alpha: 0.35),
    cardTheme: const CardThemeData(margin: EdgeInsets.symmetric(vertical: TSpace.xs + 2)),
  );
}

Color bandColor(String band) => switch (band) {
  'Excellent' => TColor.bandExcellent,
  'Good' => TColor.bandGood,
  'Fair' => TColor.bandFair,
  _ => TColor.bandBuilding,
};

/// Animation length that honours the platform "reduce motion" setting.
Duration motion(BuildContext context, int millis) =>
    MediaQuery.maybeDisableAnimationsOf(context) ?? false ? Duration.zero : Duration(milliseconds: millis);
