# vim: set ts=4 sws=4 sw=4:

# from utils import *
from utils import _n, _ext, _n_item, get_namespace
from parameter import *
from resource_classes import _resource_classes
from cppreply import CppReply
from cppcookie import CppCookie

_templates = {}

_templates['void_request_function'] = \
'''\
template<typename Connection, typename ... Parameter>
void
%s_checked(Connection && c, Parameter && ... parameter)
{
  xpp::generic::check(std::forward<Connection>(c),
                      xcb_%s_checked(std::forward<Connection>(c),
                                     std::forward<Parameter>(parameter) ...));
}

template<typename ... Parameter>
void
%s(Parameter && ... parameter)
{
  xcb_%s(std::forward<Parameter>(parameter) ...);
}
'''

def _void_request_function(name):
    return _templates['void_request_function'] % \
            ( name
            , name
            , name
            , name
            )

_templates['reply_request_function'] = \
'''\
template<typename Connection, typename ... Parameter>
reply::%s<Connection, xpp::generic::checked_tag>
%s(Connection && c, Parameter && ... parameter)
{
  return reply::%s<Connection, xpp::generic::checked_tag>(
      std::forward<Connection>(c), std::forward<Parameter>(parameter) ...);
}

template<typename Connection, typename ... Parameter>
reply::%s<Connection, xpp::generic::unchecked_tag>
%s_unchecked(Connection && c, Parameter && ... parameter)
{
  return reply::%s<Connection, xpp::generic::unchecked_tag>(
      std::forward<Connection>(c), std::forward<Parameter>(parameter) ...);
}
'''

def _reply_request_function(name):
    return _templates['reply_request_function'] % \
            ( name
            , name
            , name
            , name
            , name
            , name)

_templates['inline_reply_class'] = \
'''\
    template<typename ... Parameter>
    reply::%s<Connection, xpp::generic::checked_tag>
    %s(Parameter && ... parameter)
    {
      return xpp::%s::%s(
          static_cast<connection &>(*this).get(),
          %s\
          std::forward<Parameter>(parameter) ...);
    }

    template<typename ... Parameter>
    reply::%s<Connection, xpp::generic::unchecked_tag>
    %s_unchecked(Parameter && ... parameter)
    {
      return xpp::%s::%s_unchecked(
          static_cast<connection &>(*this).get(),
          %s\
          std::forward<Parameter>(parameter) ...);
    }
'''

def _inline_reply_class(request_name, method_name, member, ns):
    return _templates['inline_reply_class'] % \
            ( request_name
            , method_name
            , ns
            , request_name
            , member
            , request_name
            , method_name
            , ns
            , request_name
            , member
            )

_templates['inline_void_class'] = \
'''\
    template<typename ... Parameter>
    void
    %s_checked(Parameter && ... parameter)
    {
      xpp::%s::%s_checked(static_cast<connection &>(*this).get(),
                          %s\
                          std::forward<Parameter>(parameter) ...);
    }

    template<typename ... Parameter>
    void
    %s(Parameter && ... parameter)
    {
      xpp::%s::%s(static_cast<connection &>(*this).get(),
                  %s\
                  std::forward<Parameter>(parameter) ...);
    }
'''

def _inline_void_class(request_name, method_name, member, ns):
    return _templates['inline_void_class'] % \
            ( method_name
            , ns
            , request_name
            , member
            , method_name
            , ns
            , request_name
            , member
            )

_templates['void_constructor'] = \
"""\
    %s(xcb_connection_t * c%s)
    {%s
      request::operator()(c%s);
    }
"""

_templates['void_operator'] = \
"""\
    void
    operator()(xcb_connection_t * c%s) const
    {%s
      request::operator()(c%s);
    }
"""

_templates['void_request_head'] = \
"""\
namespace %s {%s namespace request {

class %s
  : public xpp::generic::%s::request<
        %s\
        FUNCTION_SIGNATURE(%s)>
{
  public:
    %s(void)
    {}
"""

_templates['void_request_tail'] = \
"""\
}; // class %s

}; };%s // request::%s%s
"""

_templates['reply_request'] = \
"""\
    %s(xcb_connection_t * c%s)
      // : request(c), m_c(c)
      : m_c(c)
    {%s
      request::prepare(c%s);
    }
"""

_templates['reply_request_head'] = \
"""\
namespace %s {%s namespace request {

class %s
  : public xpp::generic::%s::request<
        %s\
        FUNCTION_SIGNATURE(%s_reply),
        FUNCTION_SIGNATURE(%s)>
{
  public:
"""

_templates['reply_request_tail'] = \
"""\
%s\

  protected:
    operator xcb_connection_t * const(void) const
    {
      return m_c;
    }

  private:
    xcb_connection_t * m_c;
}; // class %s
%s\
}; };%s // request::%s%s
"""

_field_accessor_template = \
'''\
      template<typename %s = %s>
      %s
      %s(void) const
      {
        return %s(*this, %s);
      }\
'''

_field_accessor_template_specialization = \
'''\
template<>
%s
%s::%s<%s>(void) const
{
  return %s;
}\
'''

_replace_special_classes = \
        { "gcontext" : "gc" }

def replace_class(method, class_name):
    cn = _replace_special_classes.get(class_name, class_name)
    return method.replace("_" + cn, "")

class CppRequest(object):
    def __init__(self, request, name, is_void, namespace, reply):
        self.request = request
        self.name = name
        self.request_name = _ext(_n_item(self.request.name[-1]))
        self.is_void = is_void
        self.namespace = namespace
        self.reply = reply
        self.c_namespace = \
            "" if namespace.header.lower() == "xproto" \
            else get_namespace(namespace)
        self.accessors = []
        self.parameter_list = ParameterList()

    def make_wrapped(self):
        self.parameter_list.make_wrapped()

    def make_proto(self):
        return "  class " + self.name + ";"

    def make_class(self):
        cppcookie = CppCookie(self.namespace, self.is_void, self.request.name, self.reply, self.parameter_list)

        if self.is_void:
            void_functions = cppcookie.make_void_functions()
            if len(void_functions) > 0:
                return void_functions
            else:
                return _void_request_function(self.request_name)

        else:
            cppreply = CppReply(self.namespace, self.request.name, cppcookie, self.reply, self.accessors, self.parameter_list)
            return cppreply.make() + "\n\n" + _reply_request_function(self.request_name)

    def make_object_class_inline(self, is_connection, class_name=""):
        member = ""
        method_name = self.name
        if not is_connection:
            member = "*this,\n"
            method_name = replace_class(method_name, class_name)

        if self.is_void:
            return _inline_void_class(self.request_name, method_name, member, get_namespace(self.namespace))
        else:
            return _inline_reply_class(self.request_name, method_name, member, get_namespace(self.namespace))

    def add(self, param):
        self.parameter_list.add(param)

    def comma(self):
        return self.parameter_list.comma()

    def c_name(self, regular=True):
        ns = "" if self.c_namespace == "" else (self.c_namespace + "_")
        name = "xcb_" + ns + self.name

        # checked = void and not regular
        # unchecked = not void and not regular
        if not regular:
            if self.is_void:
                return name + "_checked"
            else:
                return name + "_unchecked"
        else:
            return name

    def calls(self, sort):
        return self.parameter_list.calls(sort)

    def protos(self, sort, defaults):
        return self.parameter_list.protos(sort, defaults)

    def template(self, indent="    ", tail="\n"):
        return indent + "template<typename " \
                + ", typename ".join(self.parameter_list.templates) \
                + ">" + tail \
                if len(self.parameter_list.templates) > 0 \
                else ""

    def iterator_template(self, indent="    ", tail="\n"):
        return indent + "template<typename " \
                + ", typename ".join(self.parameter_list.iterator_templates \
                                   + self.parameter_list.templates) \
                + ">" + tail \
                if len(self.parameter_list.iterator_templates) > 0 \
                else ""

    def wrapped_calls(self, sort):
        return self.parameter_list.wrapped_calls(sort)

    def wrapped_protos(self, sort, defaults):
        return self.parameter_list.wrapped_protos(sort, defaults)

    def iterator_calls(self, sort):
        return self.parameter_list.iterator_calls(sort)

    def iterator_2nd_lvl_calls(self, sort):
        return self.parameter_list.iterator_2nd_lvl_calls(sort)

    def iterator_protos(self, sort, defaults):
        return self.parameter_list.iterator_protos(sort, defaults)

    def iterator_initializers(self):
        return self.parameter_list.iterator_initializers()

    def make_accessors(self):
        return "\n".join(map(lambda a: "\n%s\n" % a, self.accessors))
