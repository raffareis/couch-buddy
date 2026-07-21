using System.Globalization;
using System.Reflection;

namespace BpBinReader;

public abstract class MetadataLoadContextTypeSchemaProvider : ITypeSchemaProvider, IDisposable {
    public virtual bool UseStringAssetIdType => true;
    public virtual bool SerializedFieldName => false;
    protected readonly MetadataLoadContext Mlc;
    protected readonly Dictionary<Guid, TypeSchema> TypeSchemaCache = [];
    protected readonly Dictionary<Guid, Type> TypeById = [];
    protected readonly Dictionary<string, Type> TypeByFullName = [];
    private readonly Dictionary<(MemberInfo, Type?), (CustomAttributeData?, bool)> m_AttributeCache = [];
    private readonly Dictionary<(Type, Type), bool> m_IsOrSubclassOfCache = [];
    private readonly Dictionary<Type, bool> m_IsListCache = [];
    protected readonly Type NonSerializedAttributeType;
    protected readonly Type SerializableAttributeType;
    protected readonly Type SerializeFieldAttributeType;
    protected readonly Type SerializeReferenceAttributeType;
    protected readonly Type UnityObjectType;
    protected readonly Type JsonIgnoreAttributeType;
    private readonly Type m_WeakResourceLinkType;
    private readonly Type m_FlagsAttributeType;
    private readonly Type m_AtributeUsageType;
    private readonly Type m_DelegateType;

    private readonly Type m_Int32Type;
    private readonly Type m_UInt32Type;
    private readonly Type m_Int64Type;
    private readonly Type m_UInt64Type;
    private readonly Type m_SingleType;
    private readonly Type m_DoubleType;
    private readonly Type m_BooleanType;
    private readonly Type m_StringType;

    private readonly Type m_ColorType;
    private readonly Type m_Color32Type;
    private readonly Type m_Vector2Type;
    private readonly Type m_Vector3Type;
    private readonly Type m_Vector4Type;
    private readonly Type m_Vector2IntType;
    private readonly Type m_RectType;
    private readonly Type m_GradientType;
    private readonly Type m_AnimationCurveType;
    private readonly Type m_ColorBlockType;

    protected abstract Type BlueprintReferenceBaseType { get; }
    protected readonly Type? IReferenceBaseType;
    public MetadataLoadContextTypeSchemaProvider(IEnumerable<string> assemblyDirectoryPaths) {
        var resolver = new PathAssemblyResolver(assemblyDirectoryPaths.SelectMany(Directory.EnumerateFiles));
        Mlc = new MetadataLoadContext(resolver);

        // Load all requested assemblies into the MLC.
        foreach (var p in assemblyDirectoryPaths.SelectMany(dir => Directory.EnumerateFiles(dir, "*.dll"))) {
            var asm = Mlc.LoadFromAssemblyPath(p);
            foreach (var t in SafeGetTypes(asm)) {
                if (t.FullName != null && !TypeByFullName.ContainsKey(t.FullName)) {
                    TypeByFullName[t.FullName] = t;
                }
            }
        }
        NonSerializedAttributeType = RequireType("System.NonSerializedAttribute");
        SerializableAttributeType = RequireType("System.SerializableAttribute");
        SerializeFieldAttributeType = RequireType("UnityEngine.SerializeField");
        SerializeReferenceAttributeType = RequireType("UnityEngine.SerializeReference");
        UnityObjectType = RequireType("UnityEngine.Object");
        JsonIgnoreAttributeType = RequireType("Newtonsoft.Json.JsonIgnoreAttribute");
        m_WeakResourceLinkType = RequireType("Kingmaker.ResourceLinks.WeakResourceLink");
        m_FlagsAttributeType = RequireType("System.FlagsAttribute");
        m_AtributeUsageType = RequireType("System.AttributeUsageAttribute");
        m_DelegateType = RequireType("System.Delegate");

        m_Int32Type = RequireType("System.Int32");
        m_UInt32Type = RequireType("System.UInt32");
        m_Int64Type = RequireType("System.Int64");
        m_UInt64Type = RequireType("System.UInt64");
        m_SingleType = RequireType("System.Single");
        m_DoubleType = RequireType("System.Double");
        m_BooleanType = RequireType("System.Boolean");
        m_StringType = RequireType("System.String");

        m_ColorType = RequireType("UnityEngine.Color");
        m_Color32Type = RequireType("UnityEngine.Color32");
        m_Vector2Type = RequireType("UnityEngine.Vector2");
        m_Vector3Type = RequireType("UnityEngine.Vector3");
        m_Vector4Type = RequireType("UnityEngine.Vector4");
        m_Vector2IntType = RequireType("UnityEngine.Vector2Int");
        m_RectType = RequireType("UnityEngine.Rect");
        m_GradientType = RequireType("UnityEngine.Gradient");
        m_AnimationCurveType = RequireType("UnityEngine.AnimationCurve");
        m_ColorBlockType = RequireType("UnityEngine.UI.ColorBlock");

        IReferenceBaseType = RequireType("Kingmaker.Blueprints.Base.IReferenceBase", false);
    }
    /// <summary>
    /// Turns an enum number into its string representation (displaying flag enums by using | as separator).
    /// If the enum number has no valid representation, the representation will be the numeric value itself.
    /// </summary>
    /// <param name="t">TypeSchema of the enum</param>
    /// <param name="value">Enum value to represent</param>
    /// <param name="representation">Either a string if a representation exists or a boxed long if not</param>
    /// <returns>True if a valid representation exists, False otherwise</returns>
    public bool GetEnumName(TypeSchema t, object value, out object representation) {
        var fields = t.Type.GetFields(BindingFlags.Public | BindingFlags.Static);
        var underlyingType = GetRuntimePrimitiveTypeFromMetadataType(Enum.GetUnderlyingType(t.Type));
        object rawValue = Convert.ChangeType(value, underlyingType, CultureInfo.InvariantCulture);
        long convertedValue = Convert.ToInt64(rawValue);
        if (HasAttribute(t.Type, m_FlagsAttributeType)) {
            var matching = fields
                .Where(f => (Convert.ToInt64(f.GetRawConstantValue()) & convertedValue) != 0)
                .Select(f => f.Name);
            if (!matching.Any()) {
                representation = convertedValue;
                return false;
            } else {
                representation = string.Join(" | ", matching);
                return true;
            }
        } else {
            try {
                representation = fields.First(f => Convert.ToInt64(f.GetRawConstantValue()) == convertedValue).Name;
                return true;
            } catch (Exception) {
                representation = convertedValue;
                return false;
            }
        }
    }
    public TypeSchema Resolve(Guid typeId) {
        if (typeId == Guid.Empty) {
            throw new ArgumentException("TypeId is empty.", nameof(typeId));
        }

        if (!TypeById.TryGetValue(typeId, out var t)) {
            throw new KeyNotFoundException($"TypeId {typeId:N} was not found in provided assemblies.");
        }

        if (!TypeSchemaCache.TryGetValue(typeId, out var schema)) {
            schema = BuildSchema(t, typeId);
            TypeSchemaCache[typeId] = schema;
        }

        return schema;
    }

    public void Dispose() {
        Mlc.Dispose();
    }
    #region GameSpecific
    // Re-implement ReflectionBasedSerializer.GenericObject call chain
    private static Dictionary<Type, IEnumerable<FieldInfo>> s_UnitySerializedFieldsCache = [];
    protected IEnumerable<FieldInfo> GetUnitySerializedFields(Type type) {
        if (!s_UnitySerializedFieldsCache.TryGetValue(type, out var fields)) {
            fields = InternalGetUnitySerializedFields(type);
            s_UnitySerializedFieldsCache[type] = fields;
        }
        return fields;
    }
    protected abstract IEnumerable<FieldInfo> InternalGetUnitySerializedFields(Type type);
    // ReflectionBasedSerializer.IsIdentifiedType
    protected abstract bool IsIdentifiedType(Type type);
    protected abstract TypeSchema BuildSchema(Type type, Guid typeId);
    #endregion
    #region SchemaBuilderBase

    protected virtual ValueSchema BuildValueSchema(Type fieldType, bool forceNeedsType = false) {
        if (fieldType == m_Int32Type) {
            return ValueSchema.Int32();
        }
        if (fieldType == m_UInt32Type) {
            return ValueSchema.UInt32();
        }
        if (fieldType == m_Int64Type) {
            return ValueSchema.Int64();
        }
        if (fieldType == m_UInt64Type) {
            return ValueSchema.UInt64();
        }
        if (fieldType == m_SingleType) {
            return ValueSchema.Single();
        }
        if (fieldType == m_DoubleType) {
            return ValueSchema.Double();
        }
        if (fieldType == m_BooleanType) {
            return ValueSchema.Boolean();
        }
        if (fieldType == m_StringType) {
            return ValueSchema.String();
        }

        if (fieldType.IsEnum) {
            // Produce a TypeSchema for the enum so GetEnumName can map numeric->name using metadata.
            var enumSchema = BuildSchema(fieldType, default);
            return ValueSchema.EnumInt32(enumSchema);
        }

        if (fieldType == m_ColorType) {
            return ValueSchema.Color();
        }
        if (fieldType == m_Color32Type) {
            return ValueSchema.Color32();
        }
        if (fieldType == m_Vector2Type) {
            return ValueSchema.Vector2();
        }
        if (fieldType == m_Vector3Type) {
            return ValueSchema.Vector3();
        }
        if (fieldType == m_Vector4Type) {
            return ValueSchema.Vector4();
        }
        if (fieldType == m_Vector2IntType) {
            return ValueSchema.Vector2Int();
        }
        if (fieldType == m_RectType) {
            return ValueSchema.Rect();
        }
        if (fieldType == m_GradientType) {
            return ValueSchema.Gradient();
        }
        if (fieldType == m_AnimationCurveType) {
            return ValueSchema.AnimationCurve();
        }
        if (fieldType == m_ColorBlockType) {
            return ValueSchema.ColorBlock();
        }

        if (fieldType.IsArray) {
            var elementType = fieldType.GetElementType()
                ?? throw new NotSupportedException($"Array element type missing for {fieldType.FullName ?? fieldType.Name}.");

            return ValueSchema.Array(BuildValueSchema(elementType, forceNeedsType));
        }

        if (IsList(fieldType)) {
            var elementType = fieldType.GetGenericArguments()[0];
            return ValueSchema.List(BuildValueSchema(elementType, forceNeedsType));
        }

        if (IsOrSubclassOf(fieldType, UnityObjectType)) {
            return ValueSchema.UnityObjectRef();
        }

        if (IsOrSubclassOf(fieldType, BlueprintReferenceBaseType) || (IReferenceBaseType != null && fieldType.GetInterface(IReferenceBaseType.FullName!) != null)) {
            return ValueSchema.BlueprintRef();
        }

        if (IsOrSubclassOf(fieldType, m_WeakResourceLinkType)) {
            return ValueSchema.WeakResourceLink();
        }

        var isIdentified = IsIdentifiedType(fieldType);

        TypeSchema schema;
        if (isIdentified) {
            schema = new TypeSchema(fieldType.Name, fieldType.FullName ?? fieldType.Name, [], typeof(object), default);
        } else {
            schema = BuildSchema(fieldType, default);
        }

        return ValueSchema.Object(schema, isIdentified, forceNeedsType);
    }
    #endregion
    #region ReflectionHelper
    protected Type RequireType(string fullName, bool throwIfNull = true) {
        var t = TryGetType(fullName);
        if (t == null && throwIfNull) {
            throw new InvalidOperationException($"Type '{fullName}' not found in supplied MetadataLoadContext assemblies.");
        }
        return t!;
    }

    private Type? TryGetType(string fullName) {
        if (TypeByFullName.TryGetValue(fullName, out var t)) {
            return t;
        }
        return null;
    }
    protected bool IsList(Type t) {
        if (!m_IsListCache.TryGetValue(t, out var result)) {
            if (!t.IsGenericType) {
                return false;
            }

            var def = t.GetGenericTypeDefinition();
            result = def.FullName == "System.Collections.Generic.List`1";
            m_IsListCache[t] = result;
        }
        return result;
    }

    protected bool HasAttribute(MemberInfo member, Type? attributeType) {
        return GetAttribute(member, attributeType, out _);
    }
    protected bool GetAttribute(MemberInfo member, Type? attributeType, out CustomAttributeData? data, bool? inherit = null) {
        var key = (member, attributeType);
        bool result;
        if (m_AttributeCache.TryGetValue(key, out var cached)) {
            data = cached.Item1;
            result = cached.Item2;
        } else {
            result = InternalGetAttribute(member, attributeType, out data, inherit);
            m_AttributeCache[key] = (data, result);
        }
        return result;
    }
    private bool InternalGetAttribute(MemberInfo member, Type? attributeType, out CustomAttributeData? data, bool? inherit = null) {
        data = null;
        if (attributeType == null) {
            data = null;
            return false;
        }
        if (member is Type t) {
            if (attributeType == SerializableAttributeType) {
#pragma warning disable SYSLIB0050 // Type or member is obsolete
                if (t.IsSerializable && !IsOrSubclassOf(t.UnderlyingSystemType, m_DelegateType)) {
                    return true;
                }
#pragma warning restore SYSLIB0050 // Type or member is obsolete
            } else {
                bool inherited = true;
                if (!inherit.HasValue) {
                    GetAttribute(attributeType, m_AtributeUsageType, out var usage, true);
                    if (usage == null) {
                        throw new InvalidOperationException($"AttributeUsageAttribute not found on attribute type '{t.FullName}'.");
                    }
                    foreach (var arg in usage.NamedArguments) {
                        if (arg.MemberName == nameof(AttributeUsageAttribute.Inherited)) {
                            inherited = arg.TypedValue.Value as bool? ?? true;
                            break;
                        }
                    }
                } else {
                    inherited = inherit.Value;
                }
                do {
                    data = FindAttributeType(t.CustomAttributes, attributeType);
                    if (data != null) {
                        return true;
                    }
                    try {
                        t = t.BaseType!;
                    } catch { } // e.g. I18N.CJK.ISO2022JPMode
                } while (inherited && t != null);
            }
        } else if (member is FieldInfo f && attributeType == NonSerializedAttributeType) {
#pragma warning disable SYSLIB0050 // Type or member is obsolete
            return f.IsNotSerialized;
#pragma warning restore SYSLIB0050 // Type or member is obsolete
        }
        data = FindAttributeType(member.CustomAttributes, attributeType);
        return data != null;
    }

    private CustomAttributeData? FindAttributeType(IEnumerable<CustomAttributeData> attributes, Type attributeType) {
        foreach (var data in attributes) {
            try {
                if (data.AttributeType == attributeType) {
                    return data;
                }
            } // i18n type I think
            catch { }
        }
        return null;
    }
    protected bool IsOrSubclassOf(Type t, Type baseType) {
        var key = (t, baseType);
        if (!m_IsOrSubclassOfCache.TryGetValue(key, out var result)) {
            if (t == baseType) {
                result = true;
            } else {
                result = t.IsSubclassOf(baseType);
            }
            m_IsOrSubclassOfCache[key] = result;
        }
        return result;
    }
    protected static IEnumerable<Type> SafeGetTypes(Assembly asm) {
        try {
            return asm.GetTypes();
        } catch (ReflectionTypeLoadException ex) {
            return ex.Types.Where(t => t != null).Cast<Type>().ToArray();
        }
    }
    private static Type GetRuntimePrimitiveTypeFromMetadataType(Type t) {
        return t.FullName switch {
            "System.Int32" => typeof(int),
            "System.UInt32" => typeof(uint),
            "System.Int64" => typeof(long),
            "System.UInt64" => typeof(ulong),
            "System.Byte" => typeof(byte),
            "System.SByte" => typeof(sbyte),
            "System.Int16" => typeof(short),
            "System.UInt16" => typeof(ushort),
            _ => throw new NotSupportedException($"Unsupported underlying enum type '{t.FullName}'")
        };
    }
    public virtual string GetLocalizedStringText(string key) {
        throw new NotImplementedException("Provide in the game specific provider for now.");
    }
    #endregion
}
