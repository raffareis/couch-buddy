namespace BpBinReader;

public class ValueSchema(ValueKind kind) {

    public ValueKind Kind { get; } = kind;
    public ValueSchema? Element { get; private set; }
    public TypeSchema? ObjectType { get; private set; }
    public bool IsIdentifiedType { get; private set; }
    public bool ForceNeedsType { get; private set; }

    public static ValueSchema Int32() => new(ValueKind.Int32);
    public static ValueSchema UInt32() => new(ValueKind.UInt32);
    public static ValueSchema Int64() => new(ValueKind.Int64);
    public static ValueSchema UInt64() => new(ValueKind.UInt64);
    public static ValueSchema Single() => new(ValueKind.Single);
    public static ValueSchema Double() => new(ValueKind.Double);
    public static ValueSchema Boolean() => new(ValueKind.Boolean);
    public static ValueSchema String() => new(ValueKind.String);
    public static ValueSchema EnumInt32(TypeSchema enumType) => new(ValueKind.EnumInt32) {  ObjectType = enumType };

    public static ValueSchema BlueprintRef() => new(ValueKind.BlueprintRef);

    public static ValueSchema UnityObjectRef() => new(ValueKind.UnityObjectRef);

    public static ValueSchema WeakResourceLink() => new(ValueKind.WeakResourceLink);

    public static ValueSchema LocalizedString() => new(ValueKind.LocalizedString);

    public static ValueSchema Color() => new(ValueKind.Color);
    public static ValueSchema Color32() => new(ValueKind.Color32);
    public static ValueSchema Vector2() => new(ValueKind.Vector2);
    public static ValueSchema Vector3() => new(ValueKind.Vector3);
    public static ValueSchema Vector4() => new(ValueKind.Vector4);
    public static ValueSchema Vector2Int() => new(ValueKind.Vector2Int);
    public static ValueSchema Rect() => new(ValueKind.Rect);
    public static ValueSchema Gradient() => new(ValueKind.Gradient);
    public static ValueSchema AnimationCurve() => new(ValueKind.AnimationCurve);
    public static ValueSchema ColorBlock() => new(ValueKind.ColorBlock);

    public static ValueSchema Array(ValueSchema element) => new(ValueKind.Array) { Element = element };
    public static ValueSchema List(ValueSchema element) => new(ValueKind.List) { Element = element };

    public static ValueSchema Object(TypeSchema objectType, bool isIdentifiedType, bool forceNeedsType = false) {
        return new(ValueKind.Object) { ObjectType = objectType, IsIdentifiedType = isIdentifiedType, ForceNeedsType = forceNeedsType };
    }

    // Wrath
    public static ValueSchema Bounds() => new(ValueKind.Bounds);
    public static ValueSchema BlueprintGuid() => new(ValueKind.BlueprintGuid);
    public static ValueSchema BlueprintRefWrath() => new(ValueKind.BlueprintRefWrath);
}