namespace BpBinReader;
public enum ValueKind {
    Int32,
    UInt32,
    Int64,
    UInt64,
    Single,
    Double,
    Boolean,
    String,
    EnumInt32,

    BlueprintRef,

    UnityObjectRef,

    WeakResourceLink,

    LocalizedString,

    Color,
    Color32,
    Vector2,
    Vector3,
    Vector4,
    Vector2Int,
    Rect,
    Gradient,
    AnimationCurve,
    ColorBlock,

    Array,
    List,
    Object,

    // Wrath
    BlueprintGuid,
    Bounds,
    BlueprintRefWrath
}
