import 'package:flutter/material.dart';

import '../design/theme.dart';

enum Breakpoint { compact, medium, expanded }

Breakpoint breakpointOf(BuildContext context) {
  final width = MediaQuery.sizeOf(context).width;
  if (width < TLayout.compactMax) return Breakpoint.compact;
  if (width <= TLayout.expandedMin) return Breakpoint.medium;
  return Breakpoint.expanded;
}

/// Phone width: the child as-is (identical to the mobile app).
/// Wider: the same child centred in a phone-width column on a soft branded backdrop.
class ResponsiveFrame extends StatelessWidget {
  const ResponsiveFrame({super.key, required this.child, this.maxWidth = TLayout.contentMaxWidth});

  final Widget child;
  final double maxWidth;

  @override
  Widget build(BuildContext context) {
    if (breakpointOf(context) == Breakpoint.compact) return child;
    return ColoredBox(
      color: TColor.lightPageBackdrop,
      child: Center(
        child: Container(
          constraints: BoxConstraints(maxWidth: maxWidth),
          margin: const EdgeInsets.symmetric(vertical: TSpace.xl),
          clipBehavior: Clip.antiAlias,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(TRadius.lg),
            boxShadow: const [
              BoxShadow(color: TColor.lightShadow, blurRadius: TSpace.xl, offset: Offset(0, TSpace.sm)),
            ],
          ),
          child: child,
        ),
      ),
    );
  }
}
