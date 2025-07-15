package eTactile;

@FunctionalInterface
public interface ShapeChecker3D {
  boolean isInsideShape3D(float x, float y, float z);
}