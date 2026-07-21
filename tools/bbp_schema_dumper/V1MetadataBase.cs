using System.Reflection;

namespace BpBinReader;

// V1 is the base implementation for Rogue Trader
public abstract class V1MetadataBase : MetadataLoadContextTypeSchemaProvider {
    protected override Type BlueprintReferenceBaseType { get; }
    protected readonly Type TypeIdAttributeType;
    protected readonly Type ExcludeFieldFromBuildAttributeType;
    protected readonly Type? ModsPatchSerializableAttributeType;
    protected readonly Type SimpleBlueprintType;
    protected readonly Type BlueprintComponentType;
    protected readonly Type ElementType;
    protected virtual string ExcludeFromBuildAttributeTypeName => "Kingmaker.Blueprints.JsonSystem.Helpers.ExcludeFieldFromBuildAttribute";
    protected virtual bool RequireModsPatchSerializableAttributeType => true;
    protected V1MetadataBase(IEnumerable<string> assemblyDirectoryPaths, string typeIdAttribute) : base(assemblyDirectoryPaths) {
        TypeIdAttributeType = RequireType(typeIdAttribute);
        ExcludeFieldFromBuildAttributeType = RequireType(ExcludeFromBuildAttributeTypeName);
        ModsPatchSerializableAttributeType = RequireType("Kingmaker.Blueprints.JsonSystem.Helpers.ModsPatchSerializableAttribute", RequireModsPatchSerializableAttributeType);
        SimpleBlueprintType = RequireType("Kingmaker.Blueprints.SimpleBlueprint");
        BlueprintComponentType = RequireType("Kingmaker.Blueprints.BlueprintComponent");
        ElementType = RequireType("Kingmaker.ElementsSystem.Element");
        BlueprintReferenceBaseType = RequireType("Kingmaker.Blueprints.BlueprintReferenceBase");


        foreach (var t in TypeByFullName.Values) {
            GetAttribute(t, TypeIdAttributeType, out var attr);
            if (attr != null) {
                string? guid = attr.ConstructorArguments[0].Value as string;
                if (string.IsNullOrWhiteSpace(guid)) {
                    continue;
                }

                TypeById[new(guid)] = t;
            }
        }
    }
    protected override TypeSchema BuildSchema(Type type, Guid typeId) {
        var fields = GetUnitySerializedFields(type)
            .Select(f => new FieldSchema(f.Name, BuildValueSchema(f.FieldType)))
            .ToArray();
        // Console.WriteLine($"{type.FullName}: [{string.Join(", ", fields.Select(f => f.Name))}]");
        return new TypeSchema(type.Name, type.FullName ?? type.Name, fields, type, typeId);
    }
    protected override IEnumerable<FieldInfo> InternalGetUnitySerializedFields(Type type) {
        return FieldsContractResolver_GetUnitySerializedFields(type)
            .Where(f => !HasAttribute(f, JsonIgnoreAttributeType))
            .Where(f => !HasAttribute(f, ExcludeFieldFromBuildAttributeType));
    }
    protected virtual IEnumerable<FieldInfo> FieldsContractResolver_GetUnitySerializedFields(Type type) {
        List<FieldInfo> allFields = [];
        if (type.BaseType != null) {
            allFields.AddRange(FieldsContractResolver_GetUnitySerializedFields(type.BaseType));
        }
        allFields.AddRange(type.GetFields(BindingFlags.DeclaredOnly | BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic)
            .Where(f => f.IsPublic || HasAttribute(f, SerializeFieldAttributeType))
            .Where(f => !HasAttribute(f, NonSerializedAttributeType))
            .Where(f => FieldsContractResolver_IsSerializableType(f, f.FieldType, true)));
        return allFields;
    }
    protected virtual bool FieldsContractResolver_IsSerializableType(FieldInfo field, Type? fieldType, bool arraysAllowed) {
        if (fieldType == null) {
            return false;
        }
        var fn = fieldType.FullName ?? fieldType.Name;

        if (fieldType.IsPrimitive || fieldType.IsEnum || fn == "System.String") {
            return true;
        }

        if (IsOrSubclassOf(fieldType, UnityObjectType)) {
            return true;
        }

        if (fn == "System.Object" && HasAttribute(field, ModsPatchSerializableAttributeType)) {
            return true;
        }

        if (fn == "UnityEngine.AnimationCurve"
            || fn == "UnityEngine.Rect"
            || fn == "UnityEngine.Vector2"
            || fn == "UnityEngine.Vector3"
            || fn == "UnityEngine.Vector4"
            || fn == "UnityEngine.Vector2Int"
            || fn == "UnityEngine.Vector3Int"
            || fn == "UnityEngine.Color"
            || fn == "UnityEngine.Color32"
            || fn == "UnityEngine.Gradient") {
            return true;
        }

        if (fieldType.IsArray) {
            if (!arraysAllowed) {
                return false;
            }
            return FieldsContractResolver_IsSerializableType(field, fieldType.GetElementType(), false);
        }

        if (IsList(fieldType)) {
            if (!arraysAllowed) {
                return false;
            }
            return FieldsContractResolver_IsSerializableType(field, fieldType.GetGenericArguments()[0], false);
        }

        if (HasAttribute(fieldType, SerializableAttributeType)) {
            var asmName = fieldType.Assembly.GetName().Name;
            return !string.Equals(asmName, "mscorlib", StringComparison.OrdinalIgnoreCase);
        }

        return false;
    }

    protected override bool IsIdentifiedType(Type t) {
        return IsOrSubclassOf(t, SimpleBlueprintType) || IsOrSubclassOf(t, BlueprintComponentType) || IsOrSubclassOf(t, ElementType);
    }
}
