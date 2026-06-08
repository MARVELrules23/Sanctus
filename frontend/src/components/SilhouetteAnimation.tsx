import React, { useEffect, useMemo, useRef, useState } from "react";
import { StyleSheet, View, ViewStyle } from "react-native";
import Svg, { Circle, Line, Path } from "react-native-svg";

import { MotionMode } from "@/src/utils/motion-classifier";

type Props = {
  mode: MotionMode;
  paused?: boolean;
  size?: number;
  color?: string;
  accentColor?: string;
  style?: ViewStyle;
};

/**
 * Reverent stick-figure silhouette that loops a small motion based on `mode`.
 * Joint positions are computed each tick from a 0→1 normalized phase.
 *
 * Canvas: 200 × 260 viewBox, centered figure.
 *  - head center  (100, 50), radius 18
 *  - neck         (100, 70)
 *  - shoulders    (76, 90) (124, 90)
 *  - pelvis       (100, 150)
 *  - hips         (84, 152) (116, 152)
 *  - knees baseline   (84, 195) (116, 195)
 *  - ankles baseline  (84, 245) (116, 245)
 */
const W = 200;
const H = 260;

const COLOR_DEFAULT = "#1C2841";
const COLOR_ACCENT_DEFAULT = "#D4AF37";

function rad(deg: number) {
  return (deg * Math.PI) / 180;
}

function rotateAround(
  px: number,
  py: number,
  cx: number,
  cy: number,
  angleDeg: number,
): [number, number] {
  const a = rad(angleDeg);
  const dx = px - cx;
  const dy = py - cy;
  const cos = Math.cos(a);
  const sin = Math.sin(a);
  return [cx + dx * cos - dy * sin, cy + dx * sin + dy * cos];
}

type Pose = {
  // shoulder rotation in degrees (positive = arm forward/up)
  leftShoulder: number;
  rightShoulder: number;
  leftElbow: number; // bend (0 = straight, 90 = right angle)
  rightElbow: number;
  // hip rotation
  leftHip: number;
  rightHip: number;
  leftKnee: number; // bend
  rightKnee: number;
  // body / centerline offset
  bodyTiltDeg: number; // rotation of whole body around pelvis
  bodyDropY: number; // vertical translate
  bodyShiftX: number; // horizontal translate
  headTilt: number; // not used as separate transform — wrapped with body
};

const NEUTRAL: Pose = {
  leftShoulder: 10,
  rightShoulder: -10,
  leftElbow: 15,
  rightElbow: 15,
  leftHip: 5,
  rightHip: -5,
  leftKnee: 5,
  rightKnee: 5,
  bodyTiltDeg: 0,
  bodyDropY: 0,
  bodyShiftX: 0,
  headTilt: 0,
};

/** Smooth easing 0..1. */
function ease(t: number) {
  return 0.5 - 0.5 * Math.cos(Math.PI * 2 * t);
}

function poseForMode(mode: MotionMode, p: number): Pose {
  // p is in [0,1); cycles seamlessly
  const e = ease(p);
  const e2 = ease((p + 0.5) % 1);

  switch (mode) {
    case "breathing": {
      // Slow chest rise; arms hanging slightly forward
      const lift = Math.sin(p * Math.PI * 2) * 4;
      return {
        ...NEUTRAL,
        leftShoulder: 10 + lift * 0.5,
        rightShoulder: -10 - lift * 0.5,
        bodyDropY: -lift * 0.5,
      };
    }
    case "punch": {
      // Alternating jab / cross
      // 0..0.5 = left jab extends; 0.5..1 = right cross
      const leftPunch = e; // 0..1..0
      const rightPunch = e2;
      return {
        ...NEUTRAL,
        leftShoulder: 10 + 70 * leftPunch,
        leftElbow: 70 - 65 * leftPunch,
        rightShoulder: -10 - 70 * rightPunch,
        rightElbow: 70 - 65 * rightPunch,
        bodyTiltDeg: -3 * (leftPunch - rightPunch),
        bodyShiftX: 1 * (leftPunch - rightPunch),
      };
    }
    case "elbow": {
      // Horizontal elbow swing, alternating
      const swing = Math.sin(p * Math.PI * 2);
      return {
        ...NEUTRAL,
        leftShoulder: 30 + 30 * Math.max(0, swing),
        leftElbow: 100,
        rightShoulder: -30 - 30 * Math.max(0, -swing),
        rightElbow: 100,
        bodyTiltDeg: -4 * swing,
      };
    }
    case "knee": {
      // Alternating knee strike, lift one leg high with knee bent
      const phase = p * 2; // two strikes per cycle
      const leftKneeStrike = Math.max(0, Math.sin(phase * Math.PI));
      const rightKneeStrike = Math.max(0, Math.sin((phase - 1) * Math.PI));
      return {
        ...NEUTRAL,
        leftHip: 5 - 70 * leftKneeStrike,
        leftKnee: 5 + 90 * leftKneeStrike,
        rightHip: -5 + 70 * rightKneeStrike,
        rightKnee: 5 + 90 * rightKneeStrike,
        // arms pull down for clinch
        leftShoulder: 60 + 10 * (leftKneeStrike + rightKneeStrike),
        rightShoulder: -60 - 10 * (leftKneeStrike + rightKneeStrike),
        leftElbow: 90,
        rightElbow: 90,
        bodyDropY: 4 * Math.max(leftKneeStrike, rightKneeStrike),
      };
    }
    case "kick": {
      // Round kick — single leg rises and rotates across body
      const kick = e; // 0..1..0
      return {
        ...NEUTRAL,
        rightHip: -5 - 100 * kick,
        rightKnee: 5 + 40 * (1 - kick),
        leftKnee: 5 + 8 * kick,
        bodyTiltDeg: -15 * kick,
        bodyShiftX: -4 * kick,
        leftShoulder: 10 + 40 * kick,
        rightShoulder: -10 + 20 * kick,
        leftElbow: 60,
        rightElbow: 60,
      };
    }
    case "sword_cut": {
      // Suburi: vertical overhead cut, both arms together
      const lift = ease(Math.min(1, p * 2)); // wind up first half
      const drop = ease(Math.max(0, p * 2 - 1)); // strike second half
      const armUp = 1 - (1 - lift) + drop * -1; // up then down
      // Both arms above head at wind-up, swing down to centerline
      const angle = -160 * lift + 160 * drop; // -160 = straight up; 0 = forward
      return {
        ...NEUTRAL,
        leftShoulder: angle - 8,
        rightShoulder: angle + 8,
        leftElbow: 10 + 30 * (1 - Math.abs(armUp)),
        rightElbow: 10 + 30 * (1 - Math.abs(armUp)),
        bodyDropY: -2 + 6 * drop,
      };
    }
    case "sprawl": {
      // Drop down with hands forward, hips back
      const drop = e;
      return {
        ...NEUTRAL,
        bodyDropY: 30 * drop,
        leftShoulder: 70 + 20 * drop,
        rightShoulder: -70 - 20 * drop,
        leftElbow: 30 - 20 * drop,
        rightElbow: 30 - 20 * drop,
        leftHip: 30 * drop,
        rightHip: -30 * drop,
        leftKnee: 60 * drop,
        rightKnee: 60 * drop,
        bodyTiltDeg: 15 * drop,
      };
    }
    case "shrimp": {
      // Hip escape — figure lies on side; we'll approximate with a strong tilt and hip shift
      const shift = Math.sin(p * Math.PI * 2);
      return {
        ...NEUTRAL,
        bodyTiltDeg: 60,
        bodyDropY: 35,
        bodyShiftX: 12 * shift,
        leftShoulder: 60,
        rightShoulder: -60,
        leftElbow: 90,
        rightElbow: 90,
        leftHip: 50,
        rightHip: -50,
        leftKnee: 80 + 10 * shift,
        rightKnee: 80 - 10 * shift,
      };
    }
    case "squat": {
      // Standard squat down/up
      const depth = e;
      return {
        ...NEUTRAL,
        leftHip: 10 + 25 * depth,
        rightHip: -10 - 25 * depth,
        leftKnee: 10 + 70 * depth,
        rightKnee: 10 + 70 * depth,
        bodyDropY: 22 * depth,
        bodyTiltDeg: 4 * depth,
        leftShoulder: 10 + 50 * depth,
        rightShoulder: -10 - 50 * depth,
      };
    }
    case "stretch": {
      // Slow side reach
      const swing = Math.sin(p * Math.PI * 2);
      return {
        ...NEUTRAL,
        leftShoulder: 30 + 80 * Math.max(0, swing),
        rightShoulder: -30 - 80 * Math.max(0, -swing),
        leftElbow: 5,
        rightElbow: 5,
        bodyTiltDeg: 10 * swing,
      };
    }
    case "idle":
    default: {
      const breathe = Math.sin(p * Math.PI * 2) * 1.5;
      return {
        ...NEUTRAL,
        leftShoulder: 12 + breathe,
        rightShoulder: -12 - breathe,
        bodyDropY: breathe * 0.6,
      };
    }
  }
}

/** Compute SVG points for the figure at a given pose. */
function buildJoints(pose: Pose) {
  // Apply bodyTiltDeg + bodyDropY by rotating/translating around pelvis (100, 150)
  const pelvis: [number, number] = [100 + pose.bodyShiftX, 150 + pose.bodyDropY];
  const tilt = pose.bodyTiltDeg;

  // Neutral local positions relative to original origin (will then be tilted around pelvis)
  const neckLocal: [number, number] = [100, 70];
  const headLocal: [number, number] = [100, 50];
  const lShoulderLocal: [number, number] = [76, 90];
  const rShoulderLocal: [number, number] = [124, 90];
  const lHipLocal: [number, number] = [84, 152];
  const rHipLocal: [number, number] = [116, 152];

  // Apply body tilt (rotate around (100, 150) BEFORE translating)
  const rotBody = (pt: [number, number]): [number, number] => {
    const [x, y] = rotateAround(pt[0], pt[1], 100, 150, tilt);
    return [x + pose.bodyShiftX, y + pose.bodyDropY];
  };

  const neck = rotBody(neckLocal);
  const head = rotBody(headLocal);
  const lShoulder = rotBody(lShoulderLocal);
  const rShoulder = rotBody(rShoulderLocal);
  const lHip = rotBody(lHipLocal);
  const rHip = rotBody(rHipLocal);

  // Upper arm length and lower arm length
  const UPPER = 38;
  const FORE = 36;
  // Compute elbow & wrist positions for an arm given shoulder + shoulderAngle + elbowBend
  const armPoints = (
    shoulder: [number, number],
    shoulderAngleDeg: number,
    elbowBendDeg: number,
    isLeft: boolean,
  ) => {
    // Shoulder angle 0 = straight down along the body; positive = arm forward/up (toward right side of canvas for right arm,
    // mirror for left). We'll define angles relative to the downward vector after body tilt.
    const sign = isLeft ? -1 : 1;
    const dirAngle = tilt + 90 + sign * shoulderAngleDeg; // direction of upper arm in absolute degrees from +X axis
    const ex = shoulder[0] + Math.cos(rad(dirAngle)) * UPPER;
    const ey = shoulder[1] + Math.sin(rad(dirAngle)) * UPPER;
    // Forearm continues in roughly same direction but with elbow bend
    const foreDir = dirAngle - sign * elbowBendDeg;
    const wx = ex + Math.cos(rad(foreDir)) * FORE;
    const wy = ey + Math.sin(rad(foreDir)) * FORE;
    return { elbow: [ex, ey] as [number, number], wrist: [wx, wy] as [number, number] };
  };

  const THIGH = 42;
  const SHIN = 46;
  const legPoints = (
    hip: [number, number],
    hipAngleDeg: number,
    kneeBendDeg: number,
    isLeft: boolean,
  ) => {
    const sign = isLeft ? -1 : 1;
    // Downward by default; positive hipAngle lifts leg forward (negative means lift back)
    const dirAngle = tilt + 90 + sign * hipAngleDeg;
    const kx = hip[0] + Math.cos(rad(dirAngle)) * THIGH;
    const ky = hip[1] + Math.sin(rad(dirAngle)) * THIGH;
    const shinDir = dirAngle - sign * kneeBendDeg;
    const ax = kx + Math.cos(rad(shinDir)) * SHIN;
    const ay = ky + Math.sin(rad(shinDir)) * SHIN;
    return { knee: [kx, ky] as [number, number], ankle: [ax, ay] as [number, number] };
  };

  const leftArm = armPoints(lShoulder, pose.leftShoulder, pose.leftElbow, true);
  const rightArm = armPoints(rShoulder, pose.rightShoulder, pose.rightElbow, false);
  const leftLeg = legPoints(lHip, pose.leftHip, pose.leftKnee, true);
  const rightLeg = legPoints(rHip, pose.rightHip, pose.rightKnee, false);

  return {
    head,
    neck,
    pelvis,
    lShoulder,
    rShoulder,
    lHip,
    rHip,
    leftArm,
    rightArm,
    leftLeg,
    rightLeg,
  };
}

export default function SilhouetteAnimation({
  mode,
  paused = false,
  size = 220,
  color = COLOR_DEFAULT,
  accentColor = COLOR_ACCENT_DEFAULT,
  style,
}: Props) {
  // Each motion has a different period to feel natural
  const period = useMemo(() => {
    switch (mode) {
      case "breathing":
        return 4500;
      case "punch":
        return 1100;
      case "elbow":
        return 1500;
      case "knee":
        return 1400;
      case "kick":
        return 1700;
      case "sword_cut":
        return 2200;
      case "sprawl":
        return 1800;
      case "shrimp":
        return 2000;
      case "squat":
        return 2400;
      case "stretch":
        return 3500;
      case "idle":
      default:
        return 4000;
    }
  }, [mode]);

  const [phase, setPhase] = useState(0);
  const startRef = useRef<number>(Date.now());
  const pausedRef = useRef<boolean>(paused);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    pausedRef.current = paused;
  }, [paused]);

  useEffect(() => {
    startRef.current = Date.now();
    setPhase(0);
  }, [mode]);

  useEffect(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    intervalRef.current = setInterval(() => {
      if (pausedRef.current) return;
      const elapsed = Date.now() - startRef.current;
      const p = (elapsed % period) / period;
      setPhase(p);
    }, 40);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [period]);

  const pose = poseForMode(mode, paused ? 0 : phase);
  const j = buildJoints(pose);

  const strokeWidth = 6;

  return (
    <View style={[styles.wrap, { width: size, height: (size * H) / W }, style]}>
      <Svg width="100%" height="100%" viewBox={`0 0 ${W} ${H}`}>
        {/* Floor shadow ellipse */}
        <Path
          d={`M 60 ${248 + pose.bodyDropY * 0.4} Q 100 ${254 + pose.bodyDropY * 0.4} 140 ${248 + pose.bodyDropY * 0.4}`}
          stroke={accentColor}
          strokeOpacity={0.18}
          strokeWidth={3}
          strokeLinecap="round"
          fill="none"
        />
        {/* Head */}
        <Circle
          cx={j.head[0]}
          cy={j.head[1]}
          r={16}
          stroke={color}
          strokeWidth={strokeWidth}
          fill="none"
        />
        {/* Spine: neck -> pelvis */}
        <Line
          x1={j.neck[0]}
          y1={j.neck[1]}
          x2={j.pelvis[0]}
          y2={j.pelvis[1]}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Shoulder line (subtle) */}
        <Line
          x1={j.lShoulder[0]}
          y1={j.lShoulder[1]}
          x2={j.rShoulder[0]}
          y2={j.rShoulder[1]}
          stroke={color}
          strokeOpacity={0.45}
          strokeWidth={strokeWidth - 1}
          strokeLinecap="round"
        />
        {/* Left arm */}
        <Line
          x1={j.lShoulder[0]}
          y1={j.lShoulder[1]}
          x2={j.leftArm.elbow[0]}
          y2={j.leftArm.elbow[1]}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        <Line
          x1={j.leftArm.elbow[0]}
          y1={j.leftArm.elbow[1]}
          x2={j.leftArm.wrist[0]}
          y2={j.leftArm.wrist[1]}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Right arm */}
        <Line
          x1={j.rShoulder[0]}
          y1={j.rShoulder[1]}
          x2={j.rightArm.elbow[0]}
          y2={j.rightArm.elbow[1]}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        <Line
          x1={j.rightArm.elbow[0]}
          y1={j.rightArm.elbow[1]}
          x2={j.rightArm.wrist[0]}
          y2={j.rightArm.wrist[1]}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Hands (accent dots) */}
        <Circle cx={j.leftArm.wrist[0]} cy={j.leftArm.wrist[1]} r={4} fill={accentColor} />
        <Circle cx={j.rightArm.wrist[0]} cy={j.rightArm.wrist[1]} r={4} fill={accentColor} />
        {/* Hip line */}
        <Line
          x1={j.lHip[0]}
          y1={j.lHip[1]}
          x2={j.rHip[0]}
          y2={j.rHip[1]}
          stroke={color}
          strokeOpacity={0.45}
          strokeWidth={strokeWidth - 1}
          strokeLinecap="round"
        />
        {/* Left leg */}
        <Line
          x1={j.lHip[0]}
          y1={j.lHip[1]}
          x2={j.leftLeg.knee[0]}
          y2={j.leftLeg.knee[1]}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        <Line
          x1={j.leftLeg.knee[0]}
          y1={j.leftLeg.knee[1]}
          x2={j.leftLeg.ankle[0]}
          y2={j.leftLeg.ankle[1]}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Right leg */}
        <Line
          x1={j.rHip[0]}
          y1={j.rHip[1]}
          x2={j.rightLeg.knee[0]}
          y2={j.rightLeg.knee[1]}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        <Line
          x1={j.rightLeg.knee[0]}
          y1={j.rightLeg.knee[1]}
          x2={j.rightLeg.ankle[0]}
          y2={j.rightLeg.ankle[1]}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
      </Svg>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: "center", justifyContent: "center" },
});
